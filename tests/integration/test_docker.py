import os
import six

from girder_worker.utils import JobStatus
import pytest


@pytest.mark.docker
def test_docker_run(session):
    r = session.post('integration_tests/docker/test_docker_run')
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]

        log = job['log']
        assert len(log) == 1
        assert log[0] == 'hello docker!\n'

@pytest.mark.docker
def test_docker_run_volume(session):
    fixture_dir = os.path.join('..', os.path.dirname(__file__), 'fixtures')
    params = {
        'fixtureDir': fixture_dir
    }
    r = session.post('integration_tests/docker/test_docker_run_mount_volume',
                     params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]

        log = job['log']
        assert len(log) == 2
        filepath = os.path.join(fixture_dir, 'read.txt')
        with open(filepath) as fp:
            assert log[0] == fp.read()

@pytest.mark.docker
def test_docker_run_named_pipe_output(session, tmpdir):
    params = {
        'tmpDir': tmpdir
    }
    r = session.post('integration_tests/docker/test_docker_run_named_pipe_output',
                     params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]

        log = job['log']
        assert len(log) == 1
        assert log[0] == '/mnt/girder_worker/data/output_pipe'

@pytest.mark.docker
def test_docker_run_girder_file_to_named_pipe(session, test_file, test_file_in_girder, tmpdir):

    params = {
        'tmpDir': tmpdir,
        'fileId': test_file_in_girder['_id']
    }
    r = session.post('integration_tests/docker/test_docker_run_girder_file_to_named_pipe',
                     params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]

        # Remove escaped chars
        log = [str(l) for l in job['log']]
        # join and remove trailing \n added by test script
        log = ''.join(log)[:-1]
        with open(test_file) as fp:
            assert log == fp.read()

@pytest.mark.docker
def test_docker_run_file_upload_to_item(session, girder_client, test_item):

    contents = 'Balaenoptera musculus'
    params = {
        'itemId': test_item['_id'],
        'contents': contents
    }
    r = session.post('integration_tests/docker/test_docker_run_file_upload_to_item',
                     params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]

    files = list(girder_client.listFile(test_item['_id']))

    assert len(files) == 1

    file_contents = six.BytesIO()
    girder_client.downloadFile(files[0]['_id'], file_contents)
    file_contents.seek(0)

    assert file_contents.read().strip() == contents
