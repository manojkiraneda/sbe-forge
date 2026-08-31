# PPE42 application framework

The image is split into four layers:

- `vectors.S` contains the fixed exception table; `startup.s` contains the freestanding reset path.
- `runtime/` contains facilities shared by every image.
- `include/sbe/` is the runtime/module public API.
- `apps/<name>/` contains one `main` and its application-specific modules.

Configure, test, and build all applications inside the LLVM development
container with:

```sh
meson setup output/meson-apps --cross-file cross/ppe42.ini
meson test -C output/meson-apps --print-errorlogs
meson compile -C output/meson-apps
```

Build only one application by passing `-Dapp=name` and using a separate build
directory. Shared modules are listed in `runtime_sources` in `meson.build`;
applications live in separate `apps/name` directories. Each build produces an ELF,
flat binary, map, disassembly, and symbol file in its Meson build directory.

For example, build the formatted-arguments application with:

```sh
meson setup output/meson-hellowitharguments --cross-file cross/ppe42.ini \
  -Dapp=hellowitharguments
meson compile -C output/meson-hellowitharguments
```

The hello smoke test copies `Hello world` into `sbe_test_output` and
stores the snprintf return value in `sbe_test_output_length`. Their SRAM addresses
are in `output/meson-apps/hello.symbols`, allowing a simulator or debugger to inspect the
result without requiring a console device.

`sbe_snprintf` and `sbe_vsnprintf` support `%c`, `%d`, `%i`, `%s`, `%u`, `%x`,
`%X`, and `%%`. They return the full output length and always NUL-terminate a
non-empty destination, including when the output is truncated.
