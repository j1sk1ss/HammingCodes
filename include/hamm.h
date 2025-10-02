#ifndef HAMM_H_
#define HAMM_H_
#ifdef __cplusplus
extern "C" {
#endif

typedef unsigned char byte_t;

static inline byte_t get_bit_buff(const void* buf, long bit) {
    const byte_t* b = (const byte_t*)buf;
    return (b[bit / 8] >> (bit % 8)) & 1;
}

static inline void set_bit_buff(void* buf, long bit, byte_t val) {
    byte_t* b = (byte_t*)buf;
    if (val)
        b[bit / 8] |= (1 << (bit % 8));
    else
        b[bit / 8] &= ~(1 << (bit % 8));
}

static inline void toggle_bit_buff(void* buf, long bit) {
    byte_t* b = (byte_t*)buf;
    b[bit / 8] ^= (1 << (bit % 8));
}

/*
Encode input decoded data with m-pariry bits.

Params:
- src - Input decoded data.
- ss - Source size.
- out - Output location.
- os - Output size.
- m - Parity bits count.

Return encoded data.
*/
int encode_hamming(void* src, long ss, void* out, long os, long m);

/*
Decode input encoded (source) data with m-pariry bits.

Params:
- src - Input encoded (source) data.
- ss - Source size.
- out - Output location.
- os - Output size.
- m - Parity bits count.

Return decoded data.
*/
int decode_hamming(void* src, long ss, void* out, long os, long m);

#ifdef __cplusplus
}
#endif
#endif