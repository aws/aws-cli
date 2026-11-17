/* The pinned mimalloc and the malloc-family overrides as one translation
 * unit. An alias must name a definition in its own unit, so this file
 * includes the library's single-unit build rather than linking beside it.
 *
 * It replaces ten public names: malloc, free, calloc, realloc,
 * reallocarray, aligned_alloc, posix_memalign, memalign, valloc, and
 * malloc_usable_size. musl's other allocating functions, such as strdup,
 * call malloc. musl 1.2.5 also allocates internally through __libc_malloc,
 * __libc_calloc, __libc_realloc, and __libc_free (locales, atexit,
 * posix_spawn file actions); defining those too keeps musl's own allocator
 * out of the link, so every C caller (the CRT, OpenSSL, CPython, musl)
 * reaches mimalloc.
 *
 * Each libc name is an alias of a mimalloc_libc_* function defined here,
 * which no other unit defines, so the link can check which allocator each
 * name resolved to. The functions wrap mimalloc to keep the failure
 * contract of the functions they replace, which mimalloc's own functions
 * do not: they return NULL with errno unchanged, and mi_reallocarray sets
 * EOVERFLOW. Like musl's, every failed allocation sets errno to ENOMEM,
 * except that aligned_alloc and memalign set EINVAL for an alignment that
 * is not a power of two. posix_memalign reports its error only through its
 * result and leaves errno as it was.
 *
 * mimalloc's own alloc-override.c stays out (MI_MALLOC_OVERRIDE is
 * undefined): its wrappers keep mimalloc's errno behavior. */
#include "static.c"

#include <errno.h>

static inline void* nomem_if_null(void* p) {
  if mi_unlikely(p == NULL) { errno = ENOMEM; }
  return p;
}

static inline void* aligned_result(void* p, size_t alignment) {
  if mi_unlikely(p == NULL) {
    const bool valid = alignment != 0 && _mi_is_power_of_two(alignment);
    errno = valid ? ENOMEM : EINVAL;
  }
  return p;
}

void* mimalloc_libc_malloc(size_t size) {
  return nomem_if_null(mi_malloc(size));
}

void* mimalloc_libc_calloc(size_t count, size_t size) {
  return nomem_if_null(mi_calloc(count, size));
}

void* mimalloc_libc_realloc(void* p, size_t newsize) {
  return nomem_if_null(mi_realloc(p, newsize));
}

void* mimalloc_libc_reallocarray(void* p, size_t count, size_t size) {
  return nomem_if_null(mi_reallocarray(p, count, size));
}

void* mimalloc_libc_aligned_alloc(size_t alignment, size_t size) {
  return aligned_result(mi_aligned_alloc(alignment, size), alignment);
}

void* mimalloc_libc_memalign(size_t alignment, size_t size) {
  return aligned_result(mi_memalign(alignment, size), alignment);
}

void* mimalloc_libc_valloc(size_t size) {
  return nomem_if_null(mi_valloc(size));
}

int mimalloc_libc_posix_memalign(void** p, size_t alignment, size_t size) {
  const int saved = errno;
  const int result = mi_posix_memalign(p, alignment, size);
  errno = saved;
  return result;
}

void mimalloc_libc_free(void* p) __attribute__((alias("mi_free")));
size_t mimalloc_libc_malloc_usable_size(void* p) __attribute__((alias("mi_usable_size")));

#define LIBC_ALIAS(target) __attribute__((alias(#target), visibility("default")))

void* malloc(size_t size) LIBC_ALIAS(mimalloc_libc_malloc);
void free(void* p) LIBC_ALIAS(mimalloc_libc_free);
void* calloc(size_t count, size_t size) LIBC_ALIAS(mimalloc_libc_calloc);
void* realloc(void* p, size_t newsize) LIBC_ALIAS(mimalloc_libc_realloc);
void* reallocarray(void* p, size_t count, size_t size) LIBC_ALIAS(mimalloc_libc_reallocarray);
void* aligned_alloc(size_t alignment, size_t size) LIBC_ALIAS(mimalloc_libc_aligned_alloc);
int posix_memalign(void** p, size_t alignment, size_t size)
    LIBC_ALIAS(mimalloc_libc_posix_memalign);
void* memalign(size_t alignment, size_t size) LIBC_ALIAS(mimalloc_libc_memalign);
void* valloc(size_t size) LIBC_ALIAS(mimalloc_libc_valloc);
size_t malloc_usable_size(void* p) LIBC_ALIAS(mimalloc_libc_malloc_usable_size);

void* __libc_malloc(size_t size) LIBC_ALIAS(mimalloc_libc_malloc);
void* __libc_calloc(size_t count, size_t size) LIBC_ALIAS(mimalloc_libc_calloc);
void* __libc_realloc(void* p, size_t newsize) LIBC_ALIAS(mimalloc_libc_realloc);
void __libc_free(void* p) LIBC_ALIAS(mimalloc_libc_free);
