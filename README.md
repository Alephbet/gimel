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

**NOTE**: there's no free lunch. HLL isn't as accurate, especially with large experiments. [See here](https://github.com/Alephbet/gimel/issues/15) or check out [lamed](https://github.com/Alephbet/lamed) if you're looking for a more accurate, but more memory-hungry option.

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

## Advanced

### custom API endpoints

If you want to use different API endpoints, you can add your own `extra_wiring` into the `config.json` file (e.g. using
`gimel configure`).

for example, this will add a `.../prod/my_tracking_endpoint` URL pointing to the `gimel-track` lambda:

```json
{
    "redis": {
       ...
    },
    "extra_wiring": [
        {
            "lambda": {
                "FunctionName": "gimel-track",
                "Handler": "gimel.track",
                "MemorySize": 128,
                "Timeout": 3
            },
            "api_gateway": {
                "pathPart": "my_tracking_endpoint",
                "method": {
                    "httpMethod": "GET",
                    "apiKeyRequired": false,
                    "requestParameters": {
                        "method.request.querystring.namespace": false,
                        "method.request.querystring.experiment": false,
                        "method.request.querystring.variant": false,
                        "method.request.querystring.event": false,
                        "method.request.querystring.uuid": false
                    }
                }
            }
        }
    ]
}
```

see [WIRING](https://github.com/Alephbet/gimel/blob/52830737835119692f3a3c157fe090adabf58150/gimel/deploy.py#L81)

## Privacy, Ad-blockers (GDPR etc)

Gimel provides a backend for A/B test experiment data. This data is aggregated and does *not* contain any personal information at all. It merely stores the total number of actions with a certain variation against another.

As such, Gimel should meet privacy requirements of GDPR and similar privacy regulations.

Nevertheless, important disclaimers:

* I am not a lawyer, and it's entirely up to you if and how you decide to use Gimel. Please check with your local regulations and get legal advice to decide on your own.
* Some ad-blockers are extra vigilent, and would block requests with the `track` keyword in the URL. Therefore, track requests to Gimel might be blocked by default. As the library author, I make no attempts to conceal the fact that a form of tracking is necessary to run A/B tests, even if I believe it to be respecting privacy.
* Users who decide to use Gimel can, if they wish, assign a different endpoint that might get past ad-blockers, but that's entirely up to them. see [custom API endpoints](#custom-api-endpoints) on how this can be achieved.
* As with almost any tool, it can be use for good or evil. Some A/B tests can be seen as manipulative, unfair or otherwise illegitimate. Again, use your own moral compass to decide whether or not it's ok to use A/B testing, or specific A/B tests.

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

