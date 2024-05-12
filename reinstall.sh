#!/bin/bash
repo=tmc-chopper-tune

rm -fr ./$repo -y
rm -fr ~/printer_data/config/adxl_results -y

bash install.sh