import json
import time
from collections import defaultdict

from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt

from models import TestResults


def dashboard(request):
    """Main litmus dashboard"""
    return render_to_response('litmus.jade')


@csrf_exempt
@require_POST
def post(request):
    """REST API for posting litmus results.

    build -- build version (e.g., '2.0.0-1723-rel-enterprise')
    testcase -- testcase (e.g: 'lucky6')
    env -- test enviornment (e.g, 'terra')
    metric -- metric name (e.g., 'Rebalance time, sec')
    value -- metric value (e.g., 610)

    It supports multivalued query parameters.

    Sample request:
        curl -d "build=2.0.0-1723-rel-enterprise\
                 &testcase=lucky6&env=terra\
                 &metric=Latency, ms&value=555\
                 &metric=Query throughput&value=1746" \
            -X POST http://localhost:8000/litmus/post/
    """
    try:
        build = request.POST['build']
        testcase = request.POST['testcase']
        env = request.POST['env']
        metrics = request.POST.getlist('metric')
        values = request.POST.getlist('value')
    except KeyError as e:
        return HttpResponse(e, status=400)

    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    for metric, value in zip(metrics, values):
        TestResults.objects.create(build=build, testcase=testcase, env=env,
                                   metric=metric, value=value, timestamp=timestamp)
    return HttpResponse(content='Success')


@require_GET
def get(request):
    """REST API for getting litmus results.

    Sample request:
        curl http://localhost:8000/litmus/get/

    JSON response:
        [["Testcase", "Env", "Metric", "Timestamp",
         "2.0.0-1723-rel-enterprise", "2.0.0-1724-rel-enterprise"], \
         ["lucky6", "terra", "Query throughput", "2012-10-16 11:10:30",
          "1024", "610"], \
         ["mixed-2suv", "vesta", "Latency, ms", "2012-10-16 11:16:31",
         "777", ""]]
    """
    builds = TestResults.objects.values('build').order_by('build').reverse().distinct()
    all_stats = TestResults.objects.values().distinct()
    agg_stats = defaultdict(dict)
    for stat in all_stats:
        key = "%s-%s-%s" % (stat['testcase'], stat['env'], stat['metric'])
        agg_stats[key]['testcase'] = stat['testcase']
        agg_stats[key]['env'] = stat['env']
        agg_stats[key]['metric'] = stat['metric']
        agg_stats[key]['timestamp'] = stat['timestamp']
        agg_stats[key][stat['build']] = stat['value']

    response = [['Testcase', 'Env', 'Metric', 'Timestamp']
                + [row['build'] for row in builds], ]
    for key, val in agg_stats.iteritems():
        row = [val['testcase'], val['env'], val['metric'], val['timestamp'], ]
        for build in response[0][4:]:
            try:
                row.append(val[build])
            except KeyError:
                row.append('')
        response.append(row)

    return HttpResponse(json.dumps(response), mimetype='application/json')