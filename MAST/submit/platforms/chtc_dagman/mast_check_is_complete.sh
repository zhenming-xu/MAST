#!/bin/sh

date >> POST_script_output
export MAST_PLATFORM="dagman"
python //home/mayeshiba/DAG_for_MAST/mast_check_is_complete_python.py $1 $2 1>> POST_script_output 2>> POST_script_output
