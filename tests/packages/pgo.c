#include <stdint.h>

extern uint64_t __llvm_profile_get_version(void);

int main(void) {
    return __llvm_profile_get_version() != 0 ? 0 : 1;
}
