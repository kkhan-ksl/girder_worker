import girder_worker
import traceback as tb
from celery import Celery
from celery.signals import (task_prerun, task_postrun,
                            task_failure, task_success)
from .utils import JobStatus


def deserialize_job_info_spec(**kwargs):
    return girder_worker.utils.JobManager(**kwargs)


class JobSpecNotFound(Exception):
    pass


@task_prerun.connect
def gw_task_prerun(task=None, sender=None, task_id=None,
                   args=None, kwargs=None, **rest):
    """Deserialize the jobInfoSpec passed in through the headers.

    This provides the a JobManager class as an attribute of the
    task before task execution.  decorated functions may bind to
    their task and have access to the job_manager for logging and
    updating their status in girder.
    """
    try:
        # Celery 4.x API
        if hasattr(task.request, 'jobInfoSpec'):
            jobSpec = task.request.jobInfoSpec

        # Celery 3.X API
        elif task.request.headers is not None and \
                'jobInfoSpec' in task.request.headers:
            jobSpec = task.request.headers['jobInfoSpec']

        # Deprecated: This method of passing job information
        # to girder_worker is depricated. Newer versions of girder
        # pass this information automatically as apart of the
        # header metadata in the worker scheduler.
        elif 'jobInfo' in kwargs:
            jobSpec = kwargs.pop('jobInfo', {})

        else:
            raise JobSpecNotFound

        task.job_manager = deserialize_job_info_spec(**jobSpec)

        # For now,  only automatically update status if this is
        # not a child task. Otherwise child tasks completion will
        # update the parent task's jobModel in girder.
        if task.request.parent_id is None:
            task.job_manager.updateStatus(JobStatus.RUNNING)

    except JobSpecNotFound:
        task.job_manager = None
        print('Warning: No jobInfoSpec. Setting job_manager to None.')


@task_success.connect
def gw_task_success(sender=None, **rest):
    try:
        if sender.request.parent_id is None:
            sender.job_manager.updateStatus(JobStatus.SUCCESS)
    except AttributeError:
        pass


@task_failure.connect
def gw_task_failure(sender=None, exception=None,
                    traceback=None, **rest):
    try:

        msg = '%s: %s\n%s' % (
            exception.__class__.__name__, exception,
            ''.join(tb.format_tb(traceback)))

        sender.job_manager.write(msg)

        if sender.request.parent_id is None:
            sender.job_manager.updateStatus(JobStatus.ERROR)
    except AttributeError:
        pass


@task_postrun.connect
def gw_task_postrun(task=None, sender=None, task_id=None,
                    args=None, kwargs=None,
                    retval=None, state=None, **rest):
    try:
        task.job_manager._flush()
        task.job_manager._redirectPipes(False)
    except AttributeError:
        pass


class _CeleryConfig:
    CELERY_ACCEPT_CONTENT = ['json', 'pickle', 'yaml']


app = Celery(
    main=girder_worker.config.get('celery', 'app_main'),
    backend=girder_worker.config.get('celery', 'broker'),
    broker=girder_worker.config.get('celery', 'broker'))

app.config_from_object(_CeleryConfig)
