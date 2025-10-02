#include <hamm.h>

int encode_hamming(void* src, long ss, void* out, long os, long m) {
    long n = (1 << m) - 1;
    long k = n - m;

    for (long i = 0; i < (n + 7) / 8; i++) {
        ((byte_t*)out)[i] = 0;
    }

    long data_bit = 0;
    for (long i = 0; i < n; i++) {
        int is_parity = (!(i & (i + 1)));
        if (!is_parity) {
            byte_t bit = GET_BIT_BUF(src, data_bit);
            SET_BIT_BUF(out, i, bit);
            data_bit++;
        }
    }

    for (long p = 0; p < m; p++) {
        long parity_pos = (1 << p) - 1;
        byte_t parity = 0;
        for (long i = 0; i < n; i++) {
            if (i != parity_pos && ((i + 1) & (1 << p)))
                parity ^= get_bit_buff(out, i);
        }

        set_bit_buff(out, parity_pos, parity);
    }

    return 1;
}

int decode_hamming(void* src, long ss, void* out, long os, long m) {
    long n = (1 << m) - 1;
    long k = n - m;

    byte_t encoded[(n + 7) / 8];
    for (long i = 0; i < (n + 7) / 8; i++) {
        encoded[i] = ((byte_t*)src)[i];
    }

    long error_pos = 0;
    for (long p = 0; p < m; p++) {
        long parity_pos = (1 << p) - 1;
        byte_t parity = 0;
        for (long i = 0; i < n; i++) {
            if ((i + 1) & (1 << p))
                parity ^= get_bit_buff(encoded, i);
        }

        if (parity) error_pos += (1 << p);
    }

    if (error_pos) toggle_bit_buff(encoded, error_pos - 1);

    long data_bit = 0;
    for (long i = 0; i < n; i++) {
        if ((i & (i + 1)) != 0) {
            byte_t bit = get_bit_buff(encoded, i);
            set_bit_buff(out, data_bit, bit);
            data_bit++;
        }
    }

    return 1;
}
