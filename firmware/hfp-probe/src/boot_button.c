#include "boot_button.h"

bool boot_button_poll(boot_button_t *button, bool pressed, bool ready, uint32_t now_ms)
{
    if (pressed != button->raw_pressed) {
        button->raw_pressed = pressed;
        button->changed_at = now_ms;
    }
    if (!ready) {
        button->armed = false;
    }
    if ((uint32_t)(now_ms - button->changed_at) < 30) {
        return false;
    }
    button->stable_pressed = pressed;
    if (!pressed) {
        button->armed = ready;
        return false;
    }
    if (ready && button->armed) {
        button->armed = false;
        return true;
    }
    return false;
}
