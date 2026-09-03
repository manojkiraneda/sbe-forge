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
applications live in separate `apps/name` directories. The application set
includes `hello`, `hellowitharguments`, `simple_test_assembly`, `test_c`, and
`test_c_register_pressure`. Each application produces a flat binary and a
disassembly in its Meson build directory; the ELF is only an intermediate used
for those two outputs.

The `ppe42-isa` Meson test validates every application disassembly with
`tools/check_ppe42_disassembly.py`. Disassemblies are not printed during normal
successful builds.

Each application also produces a raw `.llvm-stages.txt` compiler pass dump and
unified and side-by-side HTML reports. The reports show the exact line-level
change between every consecutive LLVM IR and Machine IR stage. For the
assembly-only `simple_test_assembly` image, the report covers its shared C
runtime because the assembly source does not pass through LLVM IR.

For example, build the formatted-arguments application with:

```sh
meson setup output/meson-hellowitharguments --cross-file cross/ppe42.ini \
  -Dapp=hellowitharguments
meson compile -C output/meson-hellowitharguments
```

The hello smoke test writes `Hello world` to the shared PPE42 output buffer at
`0xFFF88000` without requiring a console device. This matches the address used
by the legacy `llvm-sbe` hello application.

`printf` supports `%c`, `%d`, `%i`, `%s`, `%u`, `%x`, `%X`, and `%%`. Each call
writes a NUL-terminated string to its own 8-byte-aligned slot in the 16 KiB
shared output buffer. The module wraps back to the beginning when the buffer is
exhausted.
