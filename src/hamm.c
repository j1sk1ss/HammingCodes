#include <hamm.h>

int encode_hamming(void* src, void* out, long m) {
    long n = (1 << m) - 1;
    long k = n - m;

    str_memset(out, 0, (n + 7) / 8);

    long data_bit = 0;
    for (long i = 0; i < n; i++) {
        int is_parity = (!(i & (i + 1)));
        if (!is_parity) {
            byte_t bit = get_bit_buff(src, data_bit);
            set_bit_buff(out, i, bit);
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

int decode_hamming(void* src, void* out, long m) {
    long n = (1 << m) - 1;
    long k = n - m;

    byte_t encoded[(n + 7) / 8];
    str_memset(encoded, 0, (n + 7) / 8);

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
        if ((i & (i + 1))) {
            byte_t bit = get_bit_buff(encoded, i);
            set_bit_buff(out, data_bit, bit);
            data_bit++;
        }
    }

    return 1;
}

long encode_hamming_array(const byte_t* in, long in_size, byte_t* out, int m) {
    long n = (1 << m) - 1;
    long k = n - m;

    long in_bits  = in_size * 8;
    long blocks   = (in_bits + k - 1) / k;
    long out_bits = blocks * n;

    str_memset(out, 0, (out_bits + 7) / 8);
    for (long b = 0; b < blocks; b++) {
        encode_hamming((void*)(in + b * k), (void*)(out + b * n), m);
    }

    return (out_bits + 7) / 8;
}

long decode_hamming_array(const byte_t* in, long in_size, byte_t* out, int m) {
    long n = (1 << m) - 1;
    long k = n - m;

    long in_bits  = in_size * 8;
    long blocks   = in_bits / n;
    long out_bits = blocks * k;

    str_memset(out, 0, (out_bits + 7) / 8);
    for (long b = 0; b < blocks; b++) {
        decode_hamming((void*)(in + b * n), (void*)(out + b * k), m);
    }

    return (out_bits + 7) / 8;
}
