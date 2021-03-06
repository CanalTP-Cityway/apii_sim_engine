# -*- coding: utf8 -*-

import Queue
import logging
import traceback
import threading
from datetime import datetime, timedelta
from apiisim.common import AlgorithmEnum, SelfDriveModeEnum, TripPartEnum, string_to_bool, \
    TransportModeEnum, PlanTripStatusEnum, parse_location_context
from apiisim.common.plan_trip import PlanTripRequestType, SelfDriveConditionType, \
    EndingSearch, PlanTripNotificationResponseType, \
    PlanTripExistenceNotificationResponseType, \
    PlanTripResponse, StartingSearch, ErrorType
from apiisim.planner import PlanTripCancellationResponse
from apiisim.planner.plan_trip_calculator import PlanTripCalculator


def log_error(func):
    def decorator(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            logging.error("Class <%s>: %s\n%s", self.__class__.__name__,
                          e, traceback.format_exc())
            raise

    return decorator


class WorkerThread(threading.Thread):
    def __init__(self, planner, params, job_queue, notification_queue):
        threading.Thread.__init__(self)
        self.exit_code = 1
        self._planner = planner
        self._params = params
        self._job_queue = job_queue
        self._notification_queue = notification_queue
        self._cancelled = False

    def stop(self):
        self._cancelled = True
        if self._trip_calculator:
            self._trip_calculator.stop()

    @log_error
    def run(self):
        trace = self._job_queue.get()
        logging.info("WorkerThread started on job %s" % trace)
        self._trip_calculator = PlanTripCalculator(self._planner, self._params, self._notification_queue)
        try:
            if not self._cancelled:
                self._trip_calculator.compute_trip(trace)
            self.exit_code = 0
        except Exception as e:
            logging.error("compute_trip(%s): %s", trace, e)
            logging.getLogger("exceptions").error("compute_trip(%s): %s\n%s", trace, e, traceback.format_exc())

    def __del__(self):
        logging.info("WorkerThread finished")


class CalculationManager(threading.Thread):
    def __init__(self, planner, params, traces, notification_queue, termination_queue):
        threading.Thread.__init__(self)
        self._planner = planner
        self._params = params
        self._traces = traces
        self._termination_queue = termination_queue
        self._notification_queue = notification_queue
        self._workers = []
        self._cancelled = False

    def stop(self):
        self._cancelled = True
        for worker in self._workers:
            worker.stop()

    @log_error
    def run(self):
        logging.info("CalculationManager thread started")
        job_queue = Queue.Queue()
        i = 0
        for trace in self._traces:
            if self._cancelled:
                continue
            i += 1
            worker = WorkerThread(self._planner, self._params, job_queue, self._notification_queue)
            self._workers.append(worker)
            job_queue.put(trace)
            worker.start()
            # Uncomment the line below to run workers sequentially.
            # This slows down performance but makes debugging much easier.
            worker.join()
            if i == self._params.MaxTrips:
                break
        for w in self._workers:
            w.join()
        self._termination_queue.put("FINISHED")
        logging.info("CalculationManager thread finished")


class PlannerProcessHandler(object):
    def __init__(self, planner, request, notification_queue=None):
        self._planner = planner
        self._request = request
        self._request_id = self._request.clientRequestId
        self._termination_queue = Queue.Queue()
        if not notification_queue:
            self._notif_queue = Queue.Queue()
        else:
            self._notif_queue = notification_queue
        self._calculation_thread = None
        self._cancelled = False

        # AccessTime is not mandatory but None value is not recognized by .xsd
        if not self._request.Departure.AccessTime:
            self._request.Departure.AccessTime = timedelta()
        if not self._request.Arrival.AccessTime:
            self._request.Arrival.AccessTime = timedelta()

    def stop(self):
        self._cancelled = True
        if self._calculation_thread:
            self._calculation_thread.stop()

    def _send_status(self, status, error=None):
        logging.debug("Sending <%s> status", status)
        answer = PlanTripResponse()
        answer.Status = status
        answer.clientRequestId = self._request_id
        if error:
            answer.errors = [error]
        self._notif_queue.put(answer)

    @log_error
    def process(self):
        try:
            trip_calculator = PlanTripCalculator(self._planner, self._request, self._notif_queue)
            traces = trip_calculator.compute_traces()
        except Exception as exc:
            logging.error("compute_traces: %s %s", exc, traceback.format_exc())
            error = ErrorType(Field="Error", Message=exc.message)
            self._send_status(PlanTripStatusEnum.SERVER_ERROR, error)
            return

        logging.info("MIS traces: %s", traces)
        self._send_status(PlanTripStatusEnum.OK)
        self._notif_queue.put(StartingSearch(MaxComposedTripSearched=len(traces), RequestId=self._request_id))

        self._calculation_thread = CalculationManager(self._planner, self._request, traces, self._notif_queue,
                                                      self._termination_queue)
        self._calculation_thread.start()

        _ = self._termination_queue.get()
        if self._cancelled:
            self._notif_queue.put(PlanTripCancellationResponse(RequestId=self._request_id))
            logging.debug("Request cancelled by client")
        else:
            self._notif_queue.put(EndingSearch(MaxComposedTripSearched=len(traces),
                                               RequestId=self._request_id,
                                               Status=PlanTripStatusEnum.OK))
            logging.info("Request finished")

    def __del__(self):
        logging.debug("Deleting ConnectionHandler instance")
        if self._calculation_thread:
            self._calculation_thread.join()
