#include <Python.h>

/* The consumer links the generated glue and combined interpreter archive. */
int main(void) {
    return Py_GetVersion()[0] == '3' ? 0 : 1;
}
