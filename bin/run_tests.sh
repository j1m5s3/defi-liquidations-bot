#!/bin/bash

# Your project directory path to be appended to PYTHONPATH
project_path=$(pwd)

args=("$@")
arg_str=""
for arg in "${args[@]}"; do
  arg_str="$arg_str $arg"
done
# Check if the directory exists
if [ -d "$project_path" ]; then
  # If PYTHONPATH is empty or unset, set it to the project path
  if [ -z "$PYTHONPATH" ]; then
    export PYTHONPATH="$project_path"
  else
    # Append the project path to the existing PYTHONPATH with a colon as a separator
    export PYTHONPATH="$PYTHONPATH:$project_path"
  fi
  # Run your Python script or command
  python bots/tests/test_orchestration.py $arg_str

else
  echo "Project directory not found: $project_path"
fi