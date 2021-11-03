# Locust load testing test suite

This directory contains a suite of tests that will simulate different user behaviours to test out the performance of our server.

## Setup

To run load tests, from this directory run `locust`
This will start the locust server at http://0.0.0.0:8089 by default, which you can access to start a swarm of users for testing.

It will connect to a backend service running at localhost:8000, which can be changed in `base.py`

Users are defined in the `users` directory, which specifies different user behaviours in the form of `task` functions.
