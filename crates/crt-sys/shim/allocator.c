#include "crt_shim.h"
#include <aws/common/allocator.h>
#ifdef AWS_CLI_USE_MIMALLOC
#include <mimalloc.h>

/*
 * The override alone would already route aws_default_allocator() here. This
 * table remains because the CRT default's realloc always allocates, copies,
 * and frees when a buffer grows, while mi_realloc can grow in place.
 */
static void *s_acquire(struct aws_allocator *allocator, size_t size) {
    (void)allocator;
    return mi_malloc(size);
}

static void s_release(struct aws_allocator *allocator, void *ptr) {
    (void)allocator;
    mi_free(ptr);
}

static void *s_realloc(struct aws_allocator *allocator, void *ptr, size_t oldsize, size_t newsize) {
    (void)allocator;
    /* Preserve the CRT default's no-op shrink and its existing contents. */
    if (ptr && newsize <= oldsize) return ptr;
    return mi_realloc(ptr, newsize);
}

static void *s_calloc(struct aws_allocator *allocator, size_t count, size_t size) {
    (void)allocator;
    /* mimalloc checks multiplication overflow and returns NULL on failure. */
    return mi_calloc(count, size);
}

struct aws_allocator *rust_crt_allocator(void) {
    static struct aws_allocator allocator = {
        .mem_acquire = s_acquire,
        .mem_release = s_release,
        .mem_realloc = s_realloc,
        .mem_calloc = s_calloc,
    };
    return &allocator;
}
#else
struct aws_allocator *rust_crt_allocator(void) { return aws_default_allocator(); }
#endif
