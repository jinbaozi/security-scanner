#include <openssl/md5.h>
#include <openssl/des.h>

void hash_password(const char *pwd) {
    unsigned char digest[16];
    MD5((unsigned char*)pwd, strlen(pwd), digest);  // RL-040: MD5 password
}

void encrypt_data(unsigned char *data, int len) {
    DES_key_schedule ks;
    DES_set_key((DES_cblock*)"12345678", &ks);  // RL-001: DES
    DES_ecb_encrypt(data, data, &ks, DES_ENCRYPT);
}
