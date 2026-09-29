idf_component_register(SRCS "main.c" "boot_hid.c" "boot_button.c" "hfp_reconnect.c" INCLUDE_DIRS "." REQUIRES bt nvs_flash driver)
