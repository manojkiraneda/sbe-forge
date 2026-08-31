project(
  'llvm-sbe-apps',
  'c',
  version: '0.1.0',
  default_options: ['c_std=c99', 'warning_level=3', 'werror=true', 'optimization=2', 'b_staticpic=false'],
)

fs = import('fs')
app_names = ['hello', 'hellowitharguments']
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
runtime_sources = files('runtime/format.c')

llvm_install_dir = meson.get_external_property('llvm_install_dir', '/opt/llvm-install')
ld_lld = find_program(llvm_install_dir / 'bin' / 'ld.lld')
llvm_objcopy = find_program('llvm-objcopy')
llvm_objdump = find_program('llvm-objdump')
llvm_nm = find_program('llvm-nm')

foreach app_name : apps_to_build
  app_dir = 'apps' / app_name
  if not fs.is_dir(app_dir)
    error('Missing application directory: ' + app_dir)
  endif

  firmware_objects = static_library(
    app_name + '-objects',
    files('vectors.S'),
    files('startup.s'),
    runtime_sources,
    files(app_dir / 'main.c'),
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
      '-Map', app_name + '.map', '--whole-archive', '@INPUT@',
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
  custom_target(
    app_name + '-disassembly',
    input: firmware,
    output: app_name + '.dis',
    command: [llvm_objdump, '-S', '--mcpu=ppe42', '@INPUT@'],
    capture: true,
    build_by_default: true,
  )
  custom_target(
    app_name + '-symbols',
    input: firmware,
    output: app_name + '.symbols',
    command: [llvm_nm, '-n', '@INPUT@'],
    capture: true,
    build_by_default: true,
  )
endforeach

format_test = executable(
  'format-test',
  runtime_sources,
  files('tests/format_test.c'),
  include_directories: sbe_include,
  native: true,
)
test('format', format_test)
