#!/bin/bash
repo=tmc-chopper-tune

rm -fr ./$repo
rm -fr ~/printer_data/config/adxl_results

bash ./tmc-chopper-tune/install.sh