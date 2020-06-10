from datetime import timedelta

from airflow.sensors.base_sensor_operator import BaseSensorOperator
from airflow.utils.db import provide_session
from airflow.utils.decorators import apply_defaults
from airflow.utils.state import State
from ergo.models import ErgoTask


class TaskRequestBatchSensor(BaseSensorOperator):
    @apply_defaults
    def __init__(
        self,
        max_requests: int,
        xcom_tasks_key: str,
        *args,
        **kwargs
    ):
        poke_interval = kwargs.get('retry_delay', timedelta(minutes=2))
        timeout = poke_interval * kwargs.get('retries', 10)
        kwargs['soft_fail'] = True
        kwargs['poke_interval'] = kwargs.get('poke_interval', poke_interval.total_seconds())
        kwargs['timeout'] = kwargs.get('timeout', timeout.total_seconds())
        super().__init__(*args, **kwargs)
        self.max_requests = max_requests
        self.xcom_tasks_key = xcom_tasks_key

    @provide_session
    def poke(self, context, session=None):
        self.log.info('Querying for %s tasks...', State.QUEUED)
        result = session.query(ErgoTask).filter_by(
            state=State.QUEUED
        ).limit(self.max_requests)
        result = list(result)
        self.log.info(f'Query result: {result}')
        if len(result) < self.max_requests and context['ti'].is_eligible_to_retry():
            return False
        elif result:
            self.xcom_push(context, self.xcom_tasks_key, result)
            return True
        else:
            return False
