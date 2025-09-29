#!/bin/bash
set -e
/bin/bash ./scripts/deploy.sh
exec make run
