# Gimel

[a Scaleable A/B testing backend in ~100 lines of code (and for free*)](http://blog.gingerlime.com/2016/a-scaleable-ab-testing-backend-in-100-lines-of-code-and-for-free/)

## What is it?

an A/B testing backend using AWS Lambda/API Gateway + Redis

Key Features:

* Highly scalable due to the nature of AWS Lambda
* High performance and low memory footprint using Redis HyperLogLog
* Cost Effective

## What does Gimel mean?

Gimel (גִּימֵל) is the 3rd letter of the Hebrew Alphabet. The letter (ג) also looks visually similar to the greek Lambda
(λ).

## Architecture

![Architecture](https://s3.amazonaws.com/gingerlime-images/gimel-architecture.png "Architecture")

### Client

I suggest looking at [Alephbet](https://github.com/Alephbet/alephbet) to get more details, but at a high level, the client runs on the end-user browser. It will randomly pick a variant and execute a javascript function to 'activate' it. When a goal is reached -- user performs a certain action, this also include the pseudo-goal of *participating* in the experiment -- then an event is sent to the backend. An event typically looks something like "experiment ABC, variant red, user participated", or "experiment XYZ, variant blue, check out goal reached".

Alephbet might send duplicate events, but each event should include a `uuid` to allow the backend to de-duplicate it. More below

### Data Store - Redis HyperLogLog

The data store keeps a tally of each event that comes into the system. Being able to count unique events (de-duplication) was important to keep an accurate count. One approach would be to store each event in an entry / database row / document, and then run some kind of a unique count on it. Or we could use a nifty algorithm called [HyperLogLog](https://en.wikipedia.org/wiki/HyperLogLog). HyperLogLog allows you to count unique counts without storing each and every item.

In terms of storage space, redis HyperLogLog offers a fixed size of 12k per counter. This gives us ample space for storing experiment data with low memory footprint.

### Backend - AWS Lambda / API Gateway

The backend had to take care of a few simple types of requests:

* track an event - receive a (HTTP) request with some json data -- experiment name, variant, goal and uuid, and then push it to redis.
* extract the counters for a specific experiment, or all experiments into some json that can be presented on the dashboard.

### Dashboard

To view (and analyze statistically) the results of the experiments, take a look at a short [snippet](http://codepen.io/anon/pen/OMOevM?editors=001) (~20 lines of coffeescript). It uses the [Abba javascript library](https://github.com/thumbtack/abba) to do the heavy lifting. It's not super-shiny, but should do the trick.

## Installation

TODO

* update `gimel.py` with your redis settings and save it
* zip the entire folder and upload to AWS Lambda
* Plug the 3 main entry points to lambda functions / API Gateway resources:
  - `gimel.track` - for tracking events from the client
  - `gimel.experiment` - for reporting experiment results for a single experiment
  - `gimel.all` - for reporting all experiment results

## Looking for the frontend in javascript?

Run your own A/B testing framework. Check out [Alephbet](https://github.com/Alephbet/alephbet).
