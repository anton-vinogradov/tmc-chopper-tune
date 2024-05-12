#!/bin/bash
repo=tmc-chopper-tune

rm -r ./$repo -y
rm -r ~/printer_data/config/adxl_results -y

bash install.sh