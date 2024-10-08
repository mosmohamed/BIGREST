# External Imports
# Import only with "import package",
# it will make explicity in the code where it came from.

# Turns all annotations into string literals.
# This is one exception to the external import rule.
from __future__ import annotations
import time

# Internal Imports
# Import only with "from x import y", to simplify the code.

from .big import BIG
from .common.exceptions import RESTAPIError
from .common.restobject import RESTObject


class BIGIP(BIG):
    """
    Defines methods to call the iControl REST API that can be used by BIG-IP.

    Arguments:
        device: Name or IP of the device to send the HTTP requests.
        username: Username used to login to the device.
        password: Password used to login to the device.
        login_provider: Login provider used to authenticate the user.
        request_token: Indicates if token a should be requested from the
            device and used for HTTP requests.
        token: Token to be used to send HTTP requests to the device.
        debug: Debug file name to be used to output the debug information.
        session_verify: Disables SSL certificate validation if set to False
        timeout: Specifies the number of seconds to wait for a response from the device.

    Exceptions:
        InvalidOptionError: Raised when invalid options are used as arguments.
    """

    def __init__(self, device: str, username: str = None,
                 password: str = None, login_provider: str = "tmos",
                 request_token: bool = False, token: str = None,
                 debug: str = None, session_verify: bool = True, timeout: int = 10) -> BIGIP:
        super().__init__(
            device=device, username=username, password=password,
            login_provider=login_provider, request_token=request_token,
            token=token, debug=debug, session_verify=session_verify, timeout=timeout)

    def task_start(self, path: str, data: dict) -> RESTObject:
        """
        Starts a task on the device.

        Sends HTTP POST and PUT requests to the iControl REST API.

        Arguments:
            path: HTTP path used in the HTTP request sent to the device.
            data: Payload that will be sent to the device.

        Exceptions:
            RESTAPIError: Raised when iControl REST API returns an error.
        """

        if self.request_token or self.refresh_token is not None:
            self._check_token()
        url = self._get_url(path)
        response = self.session.post(url, json=data, timeout=self.timeout)
        if response.status_code not in [200, 201]:
            raise RESTAPIError(response, self.debug)
        if response.json()["kind"] == "tm:asm:tasks:import-policy:import-policy-taskstate":
            id_ = response.json()["id"]
            data = {}
        else:
            id_ = response.json()["_taskId"]
            data = {"_taskState": "VALIDATING"}
        url = f"{url}/{id_}"
        if data:
            response_put = self.session.put(url, json=data, timeout=self.timeout)
            if response_put.status_code in [200, 202]:
                print(response_put.json())
        response_get = self.session.get(url, timeout=self.timeout)
        if response_get.status_code not in [200, 202]:
            raise RESTAPIError(response_get, debug=self.debug)
        return RESTObject(response_get.json())

    def task_wait(self, obj: RESTObject, interval: int = 10) -> RESTObject:
        """
        Continually queries the status of the task until it finishes.

        Sends an HTTP GET request to the iControl REST API.

        Arguments:
            obj: Object that represents the task.
            interval: The interval the queries will be made.

        Exceptions:
            RESTAPIError: Raised when iControl REST API returns an error.
        """

        if self.request_token or self.refresh_token is not None:
            self._check_token()
        path = self._get_path(obj)
        url = self._get_url(path)
        while True:
            if self.request_token or self.refresh_token is not None:
                self._check_token()
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 500 and "AsyncContext timeout" in response.text:
                print(f'AsyncContext timeout will wait {interval} seconds')
                time.sleep(interval)
            if response.status_code != 200:
                raise RESTAPIError(response, self.debug)
            if response.json()["kind"] == "tm:asm:tasks:import-policy:import-policy-taskstate":
                status = response.json()["state"]
            else:
                status = response.json()["_taskState"]
            if status == "FAILURE":
                raise RESTAPIError(response, self.debug)
            if status == "COMPLETED":
                return RESTObject(response.json())
            else:
                time.sleep(interval)

    def task_completed(self, obj: RESTObject) -> bool:
        """
        Verifies if the task is completed.

        Sends an HTTP GET request to the iControl REST API.

        Arguments:
            obj: Object that represents the task.

        Exceptions:
            RESTAPIError: Raised when iControl REST API returns an error.
        """

        if self.request_token or self.refresh_token is not None:
            self._check_token()
        path = self._get_path(obj)
        url = self._get_url(path)
        response = self.session.get(url, timeout=self.timeout)
        if response.status_code != 200:
            raise RESTAPIError(response, self.debug)
        if response.json()["kind"] == "tm:asm:tasks:import-policy:import-policy-taskstate":
            status = response.json()["state"]
        else:
            status = response.json()["_taskState"]
        if status == "FAILURE":
            raise RESTAPIError(response, self.debug)
        if status == "COMPLETED":
            return True
        else:
            return False

    def task_result(self, obj: RESTObject) -> str:
        """
        Get the result text of the task.

        Sends an HTTP GET request to the iControl REST API.

        Arguments:
            obj: Object that represents the task.

        Exceptions:
            RESTAPIError: Raised when iControl REST API returns an error.
        """

        if self.request_token or self.refresh_token is not None:
            self._check_token()
        path = self._get_path(obj)
        url = self._get_url(path)
        url = f"{url}/result"
        response = self.session.get(url, timeout=self.timeout)
        if response.status_code != 200:
            raise RESTAPIError(response, self.debug)
        if "commandResult" in response.json():
            return response.json()["commandResult"]
        else:
            return str()

    def exist(self, path: str) -> bool:
        """
        Verifies if the object exists on the device.

        Sends an HTTP GET request to the iControl REST API.

        Arguments:
            path: HTTP path used in the HTTP request sent to the device.

        Exceptions:
            RESTAPIError: Raised when iControl REST API returns an error.
        """

        if self.request_token or self.refresh_token is not None:
            self._check_token()
        url = self._get_url(path)
        response = self.session.get(url, timeout=self.timeout)
        if response.status_code == 200:
            return True
        if response.status_code == 404:
            return False
        raise RESTAPIError(response, self.debug)

    def transaction_create(self) -> RESTObject:
        """
        Create a transaction on the device.

        Sends an HTTP POST request to the iControl REST API.

        Exceptions:
            RESTAPIError: Raised when iControl REST API returns an error.
        """

        if self.request_token or self.refresh_token is not None:
            self._check_token()
        url = self._get_url("/mgmt/tm/transaction")
        response = self.session.post(url, json={}, timeout=self.timeout)
        if response.status_code != 200:
            raise RESTAPIError(response, self.debug)
        self._transaction = response.json()["transId"]
        self.session.headers.update(
            {"X-F5-REST-Coordination-Id": f"{self._transaction}"})
        return RESTObject(response.json())

    def __enter__(self) -> RESTObject:
        """
        Used in with statement.

        Calls transaction_create().
        """

        return self.transaction_create()

    def transaction_commit(self) -> RESTObject:
        """
        Commit a transaction on the device.

        Sends an HTTP PATCH request to the iControl REST API.

        Exceptions:
            RESTAPIError: Raised when iControl REST API returns an error.
        """

        if self.request_token or self.refresh_token is not None:
            self._check_token()
        url = self._get_url(f"/mgmt/tm/transaction/{self._transaction}")
        self.session.headers.pop("X-F5-REST-Coordination-Id")
        data = {}
        data["state"] = "VALIDATING"
        response = self.session.patch(url, json=data, timeout=self.timeout)
        if response.status_code != 200:
            raise RESTAPIError(response, self.debug)
        return RESTObject(response.json())

    def __exit__(self, type, value, traceback) -> None:
        """
        Used in with statement.

        Calls transaction_commit().
        """

        self.transaction_commit()

    def transaction_validate(self) -> RESTObject:
        """
        Validate a transaction on the device.

        Sends an HTTP PATCH request to the iControl REST API.

        Exceptions:
            RESTAPIError: Raised when iControl REST API returns an error.
        """

        if self.request_token or self.refresh_token is not None:
            self._check_token()
        url = self._get_url(f"/mgmt/tm/transaction/{self._transaction}")
        self.session.headers.pop("X-F5-REST-Coordination-Id")
        data = {}
        data["validateOnly"] = True
        data["state"] = "VALIDATING"
        response = self.session.patch(url, json=data, timeout=self.timeout)
        if response.status_code != 200:
            raise RESTAPIError(response, self.debug)
        else:
            self.session.headers.update(
                {"X-F5-REST-Coordination-Id": f"{self._transaction}"})
        return RESTObject(response.json())
