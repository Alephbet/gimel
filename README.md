# Gimel

A/B testing backend using AWS Lambda/API Gateway + Redis

Key Features:

* Highly scalable due to the nature of AWS Lambda
* High performance and low memory footprint using Redis HyperLogLog
* Cost Effective

## What does Gimel mean?

Gimel (גִּימֵל) is the 3rd letter of the Hebrew Alphabet. The letter (ג) also looks visually similar to the greek Lambda
(λ).

## Installation

TODO

* update `gimel.py` with your redis settings and save it
* zip the entire folder and upload to AWS Lambda
* Plug the 3 main entry points to lambda functions / API Gateway resources:
  - `gimel.track` - for tracking events from the client
  - `gimel.experiment` - for reporting experiment results for a single experiment
  - `gimel.all` - for reporting all experiment results
