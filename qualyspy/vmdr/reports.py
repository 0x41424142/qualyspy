"""
reports.py - contains functions to work with reports in VMDR.
"""

from typing import *

from requests.models import Response

from .data_classes import VMDRReport, ReportTemplate
from ..auth import BasicAuth
from ..base import call_api
from ..base import xml_parser
from .data_classes.lists import BaseList
from ..exceptions.Exceptions import *


def manage_reports(
    auth: BasicAuth,
    action: Literal["list", "launch", "cancel", "fetch", "delete"],
    **kwargs,
) -> Response:
    """
    Backend function to manage reports in Qualys VMDR.

    Parameters:
        ```auth```: ```Required[BasicAuth]``` - The BasicAuth object.
        ```action```: ```Literal["list", "launch", "cancel", "fetch", "delete"]``` - The action to take.

    Returns:
        ```Response``` - The response from the API.

    Kwargs:

    WHEN ```action=="list"```:
        ```id```: ```Optional[Union[int,str]]``` - A specific report ID to get.
        ```state```: ```Optional[str]``` - Filter output to reports in a specific state.
        ```user_login```: ```Optional[str]``` - Filter output to reports launched by a specific user.
        ```expires_before_datetime```: ```Optional[str]``` - Filter output to reports that will expire before this datetime. Formatted like: YYYY-MM-DD[THH:MM:SSZ]
        ```client_id```: ```Optional[Union[int,str]]``` - Filter output to reports for a specific client ID. ONLY VALID FOR CONSULTANT SUBSCRIPTIONS!
        ```client_name```: ```Optional[str]``` - Filter output to reports for a specific client name. ONLY VALID FOR CONSULTANT SUBSCRIPTIONS!
    """

    # Set specific kwargs
    kwargs["action"] = action
    kwargs["echo_request"] = False

    headers = {"X-Requested-With": "qualyspy SDK"}

    match action:
        
        case "list":
            return call_api(
                auth=auth,
                module="vmdr",
                endpoint="get_report_list",
                params=kwargs,
                headers=headers,
            )
        
        case "launch":
            return call_api(
                auth=auth,
                module="vmdr",
                endpoint="launch_report",
                payload=kwargs,
                headers=headers,
            )
        
        case _:
            raise NotImplementedError(f"Action {action} is not implemented yet.")


def get_report_list(auth: BasicAuth, **kwargs) -> BaseList[VMDRReport]:
    """
    Get a list of reports in VMDR, according to kwargs.

    Parameters:
        ```auth```: ```Required[BasicAuth]``` - The BasicAuth object.

    Kwargs:
        ```id```: ```Optional[Union[int,str]]``` - A specific report ID to get.
        ```state```: ```Optional[str]``` - Filter output to reports in a specific state.
        ```user_login```: ```Optional[str]``` - Filter output to reports launched by a specific user.
        ```expires_before_datetime```: ```Optional[str]``` - Filter output to reports that will expire before this datetime. Formatted like: YYYY-MM-DD[THH:MM:SSZ]
        ```client_id```: ```Optional[Union[int,str]]``` - Filter output to reports for a specific client ID. ONLY VALID FOR CONSULTANT SUBSCRIPTIONS!
        ```client_name```: ```Optional[str]``` - Filter output to reports for a specific client name. ONLY VALID FOR CONSULTANT SUBSCRIPTIONS!

    Returns:
        ```BaseList[VMDRReport]``` - A list of VMDRReport objects.
    """

    response = manage_reports(auth, action="list", **kwargs)

    data = xml_parser(response.text)

    reports = data["REPORT_LIST_OUTPUT"]["RESPONSE"]["REPORT_LIST"]["REPORT"]

    bl = BaseList()

    # Check if there are multiple reports or just one
    if isinstance(reports, dict):
        reports = [reports]

    for report in reports:
        bl.append(VMDRReport.from_dict(report))

    return bl

def get_template_list(auth: BasicAuth) -> BaseList[ReportTemplate]:
    """
    Get the list of report templates in your subscription.

    Parameters:
        ```auth```: ```Required[BasicAuth]``` - The BasicAuth object.

    Returns:
        ```BaseList[ReportTemplate]``` - A list of ReportTemplate objects.
    """

    response = call_api(
        auth=auth,
        module="vmdr",
        endpoint="get_template_list",
        headers={"X-Requested-With": "qualyspy SDK"},
    )

    data = xml_parser(response.text)

    if "SIMPLE_RETURN" in data:
        raise QualysAPIError(data["SIMPLE_RETURN"]["RESPONSE"]["TEXT"])
    
    bl = BaseList()

    templates = data["REPORT_TEMPLATE_LIST"]["REPORT_TEMPLATE"]

    # Check if there are multiple templates or just one
    if isinstance(templates, dict):
        templates = [templates]

    for template in templates:
        bl.append(ReportTemplate.from_dict(template))

    return bl


def launch_report(auth: BasicAuth, template_id: str, **kwargs) -> int:
    '''
    Generate a new report in VMDR.
    
    Parameters:
        ```auth```: ```Required[BasicAuth]``` - The BasicAuth object.
        ```template_id```: ```Union[int, str]``` - The ID of the template to use for the report.
        
    Kwargs:

        Parameter| Possible Values |Description|Required|
        |--|--|--|--|
        |```auth```|```qualyspy.auth.BasicAuth```|The authentication object.|✅|
        |```template_id```|```Union[int, str]``` |The template that the report will follow. Use ```get_report_template_list()``` To select one.|✅|
        |```report_title```|```str```|The name to give to the report. ```⚠️ IF YOU REQUEST A PCI COMPLIANCE REPORT, THE TITLE IS AUTO-GENERATED BY QUALYS!```|❌|
        |```output_format```| FOR MAP REPORT: <br> ```pdf, html, mht, xml, csv```<br>FOR SCAN REPORT:<br>```pdf, html mht, xml, csv, docx```<br>FOR REMEDIATION REPORT:<br>```pdf, html, mht, csv```<br>FOR COMPLIANCE (NON-PCI) REPORT:<br>```pdf, html, mht```<br>FOR PCI COMPLIANCE REPORT:<br>```pdf, html```<br>FOR PATCH REPORT:<br>```pdf, online, xml, csv```<br>FOR COMPLIANCY POLICY REPORT:<br>```pdf, html, mht, xml, csv```|The format that the report will be generated in.|❌|
        |```hide_header```|```True/False```| ⚠️ SDK auto-sets this to ```True```!|❌|
        |```pdf_password```|```str```|If ```output_format==pdf```, file will be encrypted with this password. Note that this is required for ```recipient_group/recipient_group_id```. <br>⚠️ REQUREMENTS:<br>1.```8<=N<=32``` characters<br>2. Must contain alpha and numeric characters<br>3.Cannot match your Qualys account's password<br>4.Must follow any other password restrictions in ```Users->Setup->Security```|❌|
        |```recipient_group```|```str```: ```"groupOne,GroupTwo"```|A comma-separated string of group that the PDF will be shared with. ⚠️ CANNOT BE IN THE SAME REQUEST WITH ```recipient_group_id```|❌|
        |```recipient_group_id```|```str```|A comma-separated string of group IDs to share the PDF with. ⚠️ CANNOT BE IN THE SAME REQUEST WITH ```recipient_group```| ❌|
        |```report_type```|```Literal["Map", "Scan", "Patch", "Remediation", "Compliance", "Policy"]```|Shape the report to a specific type.|❌|
        |```domain```|```str```| Target domain for the report.|⚠️ REQUIRED FOR MAP REPORT|
        |```ip_restriction```|Comma-separated string of IP addresses to include in a map report.|⚠️ REQUIRED FOR MAP REPORT WHEN ```domain=='None'```|
        |report_refs|```str```|Comma-separated string of reference IDs.|⚠️ REQUIRED FOR MAP REPORT, MANUAL SCAN REPORT, PCI COMPLIANCE REPORT|
        |```asset_group_ids```|```str```|Override asset group IDs defined in the report template with these IDs.|❌|
        |```ips_network_id```|```Union[int, str]```|Restrict the report to specific network IDs. ⚠️ MUST BE ENABLED IN THE QUALYS SUBSCRIPTION|❌|
        |```ips```|```str```|Comma-separated string of IP addresses to include, overwriting the report template.|❌|
        |```assignee_type```|```Literal["User", "All"]```|Specify if tickets assigned to the requesting user, or all tickets will be included in the report. Defaults to ```"User"```.|❌|
        |```policy_id```|```Union[int, str]```|The specific policy to run the report on.|❌|
        |```host_id```|```str```|In policy report output, show results for a single host. |⚠️ REQUIRED WHEN ```instance_string``` IS SPECIFIED.|
        |```instance_string```|```str```|Specifies a single instance on a host machine.|⚠️ REQUIRED WHEN ```host_id``` IS SPECIFIED.|

    Returns:
        ```int``` - The ID of the report.
        '''
    
    # Set specific kwargs
    kwargs["template_id"] = template_id

    response = manage_reports(auth, action="launch", **kwargs)

    data = xml_parser(response.text)

    try:
        return int(data["SIMPLE_RETURN"]["RESPONSE"]["ITEM_LIST"]["ITEM"]["VALUE"])
    except KeyError:
        raise QualysAPIError(data["SIMPLE_RETURN"]["RESPONSE"]["TEXT"])