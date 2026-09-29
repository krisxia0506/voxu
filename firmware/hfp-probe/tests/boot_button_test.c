#include <assert.h>
#include <stdio.h>
#include "boot_button.h"

int main(void)
{
    boot_button_t b = {0};
    assert(!boot_button_poll(&b, false, true, 30));
    assert(!boot_button_poll(&b, true, true, 100));
    assert(!boot_button_poll(&b, false, true, 110)); // contact bounce
    assert(!boot_button_poll(&b, true, true, 120));
    assert(!boot_button_poll(&b, true, true, 149));
    assert(boot_button_poll(&b, true, true, 150));
    assert(!boot_button_poll(&b, true, true, 5000)); // long hold never repeats
    assert(!boot_button_poll(&b, false, true, 5010));
    assert(!boot_button_poll(&b, true, true, 5020)); // release bounce
    assert(!boot_button_poll(&b, false, true, 5030));
    assert(!boot_button_poll(&b, false, true, 5060));
    assert(!boot_button_poll(&b, true, true, 5100));
    assert(boot_button_poll(&b, true, true, 5130)); // second press stops dictation

    assert(!boot_button_poll(&b, true, false, 5200)); // disconnect while held
    assert(!boot_button_poll(&b, true, true, 5300)); // no replay on reconnect
    assert(!boot_button_poll(&b, false, true, 5310));
    assert(!boot_button_poll(&b, false, true, 5340));
    assert(!boot_button_poll(&b, true, true, 5350));
    assert(boot_button_poll(&b, true, true, 5380));

    b = (boot_button_t){0};
    assert(!boot_button_poll(&b, true, true, 100)); // held on startup
    assert(!boot_button_poll(&b, true, true, 130));
    assert(!boot_button_poll(&b, false, true, 200));
    assert(!boot_button_poll(&b, false, true, 230));
    assert(!boot_button_poll(&b, true, true, UINT32_MAX - 10));
    assert(!boot_button_poll(&b, true, true, 10));
    assert(boot_button_poll(&b, true, true, 20)); // timer wrap
    puts("PASS: debounce, one trigger per press, startup/reconnect suppression, timer wrap");
}
