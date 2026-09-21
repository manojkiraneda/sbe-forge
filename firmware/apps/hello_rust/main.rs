#![no_std]
#![no_main]

use core::panic::PanicInfo;

const OUTPUT: *mut u8 = 0xFFF8_8000 as *mut u8;
const MESSAGE: &[u8] = b"Hello world\0";

#[no_mangle]
pub extern "C" fn main() -> ! {
    // Match firmware/apps/hello/main.c: write the message without a newline,
    // then remain in the application forever.
    unsafe {
        for (index, byte) in MESSAGE.iter().enumerate() {
            core::ptr::write_volatile(OUTPUT.add(index), *byte);
        }
    }

    loop {
        core::hint::spin_loop();
    }
}

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {
        core::hint::spin_loop();
    }
}
