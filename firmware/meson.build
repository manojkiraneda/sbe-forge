project(
  'llvm-sbe-apps',
  'c',
  version: '0.1.0',
  default_options: ['c_std=c99', 'warning_level=3', 'werror=true', 'optimization=2', 'b_staticpic=false'],
)

fs = import('fs')
app_names = [
  'hello',
  'hellowitharguments',
  'simple_test_assembly',
  'test_c',
  'test_c_register_pressure',
]
requested_app = get_option('app')
if requested_app == 'all'
  apps_to_build = app_names
elif requested_app in app_names
  apps_to_build = [requested_app]
else
  error('Unknown application: ' + requested_app)
endif

sbe_include = include_directories('include')
linker_script = meson.current_source_dir() / 'linker'

# Add shared modules here. Applications remain isolated under apps/<name>.
runtime_sources = files('runtime/printf.c')

llvm_install_dir = meson.get_external_property('llvm_install_dir', '/opt/llvm-install')
ld_lld = find_program(llvm_install_dir / 'bin' / 'ld.lld')
llvm_objcopy = find_program('llvm-objcopy')
llvm_objdump = find_program('llvm-objdump')
python = import('python').find_installation('python3')
isa_checker = meson.project_source_root() / '..' / 'tools' / 'check_ppe42_disassembly.py'
ppe42_disassemblies = []

foreach app_name : apps_to_build
  app_dir = 'apps' / app_name
  if not fs.is_dir(app_dir)
    error('Missing application directory: ' + app_dir)
  endif
  if fs.is_file(app_dir / 'main.c')
    app_source = files(app_dir / 'main.c')
  elif fs.is_file(app_dir / 'main.s')
    app_source = files(app_dir / 'main.s')
  else
    error('Missing main.c or main.s in application directory: ' + app_dir)
  endif

  firmware_objects = static_library(
    app_name + '-objects',
    files('vectors.S'),
    files('startup.s'),
    runtime_sources,
    app_source,
    include_directories: sbe_include,
    pic: false,
    c_args: [
      '-Wno-unused-command-line-argument',
      '-ffreestanding', '-fno-builtin', '-fno-stack-protector',
      '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
      '-ffunction-sections', '-fdata-sections',
    ],
    install: false,
  )

  firmware = custom_target(
    app_name + '-elf',
    input: firmware_objects,
    output: app_name + '.elf',
    command: [
      ld_lld, '-T', linker_script, '--gc-sections',
      '--whole-archive', '@INPUT@',
      '--no-whole-archive', '-o', '@OUTPUT@',
    ],
    depend_files: files('linker'),
    build_by_default: true,
  )

  custom_target(
    app_name + '-binary',
    input: firmware,
    output: app_name + '.bin',
    command: [llvm_objcopy, '-O', 'binary', '@INPUT@', '@OUTPUT@'],
    build_by_default: true,
  )
  app_disassembly = custom_target(
    app_name + '-disassembly',
    input: firmware,
    output: app_name + '.dis',
    command: [llvm_objdump, '-S', '--mcpu=ppe42', '@INPUT@'],
    capture: true,
    build_by_default: true,
  )
  ppe42_disassemblies += [app_disassembly]
endforeach

printf_test = executable(
  'printf-test',
  runtime_sources,
  files('tests/printf_test.c'),
  include_directories: sbe_include,
  c_args: ['-D_GNU_SOURCE', '-Dprintf=sbe_test_printf'],
  native: true,
)
test('printf', printf_test)

test(
  'ppe42-isa',
  python,
  args: [isa_checker, '--variant', 'ppe42xm'] + ppe42_disassemblies,
  depends: ppe42_disassemblies,
)
