# Gimel

[![Build Status](https://travis-ci.org/Alephbet/gimel.svg?branch=master)](https://travis-ci.org/Alephbet/gimel)
[![PyPI](https://img.shields.io/pypi/v/gimel.svg)](https://pypi.python.org/pypi/gimel)

[a Scaleable A/B testing backend in ~100 lines of code (and for free*)](http://blog.gingerlime.com/2016/a-scaleable-ab-testing-backend-in-100-lines-of-code-and-for-free/)

## What is it?

an A/B testing backend using AWS Lambda/API Gateway + Redis

Key Features:

* Highly scalable due to the nature of AWS Lambda
* High performance and low memory footprint using Redis HyperLogLog
* Cost Effective
* Easy deployment using `gimel deploy`. No need to twiddle with AWS.

## Looking for contributors

[click here for more info](https://github.com/Alephbet/gimel/issues/2)

## What does Gimel mean?

Gimel (גִּימֵל) is the 3rd letter of the Hebrew Alphabet. The letter (ג) also looks visually similar to the greek Lambda
(λ).

## Installation / Quick Start

You will need a live instance of redis accessible online from AWS. Then run:

```bash
$ pip install gimel
$ gimel configure
$ gimel deploy
```

![](https://s3.amazonaws.com/gingerlime-images/gimel-deploy.gif "gimel deploy")

It will automatically configure your AWS Lambda functions, API gateway and produce a JS snippet ready to use
for tracking your experiments.

## Architecture

![](https://s3.amazonaws.com/gingerlime-images/gimel-architecture.png "Architecture")

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

New! access your dashboard with `gimel dashboard`

![](https://s3.amazonaws.com/gingerlime-images/gimel-dashboard.gif "gimel dashboard")

## How does tracking work?

Check out [Alephbet](https://github.com/Alephbet/alephbet).

## Command Reference

* `gimel --help` - prints a help screen.
* `gimel configure` - opens your editor so you can edit the config.json file. Use it to update your redis settings.
* `gimel preflight` - runs preflight checks to make sure you have access to AWS, redis etc.
* `gimel deploy` - deploys the code and configs to AWS automatically.

## License

Gimel is distributed under the MIT license. All 3rd party libraries and components are distributed under their
respective license terms.

```
Copyright (C) 2016 Yoav Aner

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

