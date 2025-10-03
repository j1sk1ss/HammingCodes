#include <mm.h>

static unsigned char _buffer[ALLOC_BUFFER_SIZE] = { 0 };
static mm_block_t* _mm_head = (mm_block_t*)_buffer;

int ll_init() {
    if (_mm_head->magic != MM_BLOCK_MAGIC) {
        _mm_head->magic = MM_BLOCK_MAGIC;
        _mm_head->size  = ALLOC_BUFFER_SIZE - sizeof(mm_block_t);
        _mm_head->free  = 1;
        _mm_head->next  = NULL;
    }
    
    return 1;
}

static int __ll_coalesce_memory() {
    int merged = 0;
    mm_block_t* current = _mm_head;
    
    do {
        merged = 0;
        current = _mm_head;

        while (current && current->magic == MM_BLOCK_MAGIC && current->next) {
            if (current->free && current->next->free) {
                current->size += sizeof(mm_block_t) + current->next->size;
                current->next = current->next->next;
                merged = 1;
            } 
            else {
                current = current->next;
            }
        }
    } while (merged);
    return 1;
}

static void* __ll_malloc(unsigned int size, unsigned int offset, int prepare_mem) {
    if (!size) return NULL;
    if (prepare_mem) __ll_coalesce_memory();

    size   = (size + (ALIGNMENT - 1)) & ~(ALIGNMENT - 1);
    offset = (offset + (ALIGNMENT - 1)) & ~(ALIGNMENT - 1);
    mm_block_t* current = _mm_head;
    
    while (current && current->magic == MM_BLOCK_MAGIC) {
        void* aligned_addr = (unsigned char*)current + sizeof(mm_block_t);
        unsigned int position = (unsigned int)((unsigned char*)aligned_addr - _buffer);
        if (current->free && current->size >= size && position >= offset) {
            if (current->size >= size + sizeof(mm_block_t)) {
                mm_block_t* new_block = (mm_block_t*)((unsigned char*)current + sizeof(mm_block_t) + size);
                new_block->magic = MM_BLOCK_MAGIC;
                new_block->size = current->size - size - sizeof(mm_block_t);
                new_block->free = 1;
                new_block->next = current->next;

                current->next = new_block;
                current->size = size;
            }

            current->free = 0;
            return (unsigned char*)current + sizeof(mm_block_t);
        }

        current = current->next;
    }

    return prepare_mem ? NULL : __ll_malloc(size, offset, 1);
}

void* ll_malloc(unsigned int size) {
    return __ll_malloc(size, NO_OFFSET, 0);
}

void* ll_mallocoff(unsigned int size, unsigned int offset) {
    return __ll_malloc(size, offset, 0);
}

int ll_free(void* ptr) {
    if (!ptr || ptr < (void*)_buffer || ptr >= (void*)(_buffer + ALLOC_BUFFER_SIZE)) {
        return 0;
    }
    
    mm_block_t* block = (mm_block_t*)((unsigned char*)ptr - sizeof(mm_block_t));
    if (block->magic != MM_BLOCK_MAGIC) return 0;
    if (block->free) return 0;

    block->free = 1;
    return 1;
}

