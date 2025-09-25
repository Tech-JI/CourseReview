#!/bin/bash
set -e
/bin/bash ./deploy.sh
exec make run
