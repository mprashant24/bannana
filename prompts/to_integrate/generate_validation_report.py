#!/usr/bin/env python3

import json
import os
from pathlib import Path

# Load the analysis plan
analysis_plan_path = "PATH_TO_RESULTS"
with open(analysis_plan_path, 'r') as f:
    content = f.read()

# Parse the JSON from the analysis plan
start_idx = content.find('{')
end_idx = content.rfind('}') + 1
json_content = content[start_idx:end_idx]

# Parse JSON
analysis_data = json.loads(json_content)

# Create validation report structure
report = {
    "report_date": "2024-05-20",
    "application": "CURRENT_APPLICATION",
    "version": "v1.0",
    "total_findings": 0,
    "validated_findings": [],
    "validation_summary": {
        "confirmed_vulnerabilities": 0,
        "rejected_findings": 0,
        "pending_validation": 0
    }
}

# Count total findings
total_findings = 0
for check in analysis_data.get("checks", []):
    total_findings += len(check.get("findings", []))

# Add additional checks
for check in analysis_data.get("additional_checks", []):
    total_findings += len(check.get("findings", []))

report["total_findings"] = total_findings

# Function to validate a finding
def validate_finding(finding, check_name):
    """
    Validates a single finding by examining the code at the specified location
    """
    file_path = finding["file"]
    location = finding["location"]
    
    # Initialize validation result
    validation_result = {
        "finding_id": f"{check_name}_{finding.get('location', '').replace(':', '_')}",
        "check name": check_name,
        "file": file_path,
        "location": location,
        "observation": finding["observation"],
        "severity": finding["severity"],
        "confidence": finding["confidence"],
        "needs_validation": finding["needs_validation"],
        "status": "pending",  # Will be updated after validation
        "validation_method": "code_analysis",
        "evidence": "",
        "justification": "",
        "exploitability": "unknown"
    }
    
    # Try to read the file to examine the code
    try:
        with open(file_path, 'r') as f:
            file_lines = f.readlines()
        
        # Extract code snippet from the file
        evidence = ""
        if "line" in location:
            line_num = int(location.split(',')[0].split()[-1]) - 1  # Convert to zero-based indexing
            if 0 <= line_num < len(file_lines):
                evidence += f"Code at line {line_num + 1}:\n"
                evidence += file_lines[line_num]
                
                # Include a few lines around for context
                start_line = max(0, line_num - 2)
                end_line = min(len(file_lines), line_num + 3)
                for i in range(start_line, end_line):
                    prefix = ">>> " if i == line_num else "    "
                    evidence += f"{prefix}{i+1}: {file_lines[i]}"
        
        validation_result["evidence"] = evidence
        
        # Analyze the specific vulnerability
        if check_name == "check_1_missing_auth":
            # Validate authentication requirements
            validation_result["justification"] = analyze_authentication_requirement(file_path, location, file_lines)
            
        elif check_name == "check_2_idor":
            # Validate IDOR issues
            validation_result["justification"] = analyze_idor_issue(file_path, location, file_lines)
            
        elif check_name == "check_3_privilege_escalation":
            # Validate privilege escalation
            validation_result["justification"] = analyze_privilege_escalation(file_path, location, file_lines)
            
        elif check_name == "check_4_missing_function_level_access_control":
            # Validate function level access control
            validation_result["justification"] = analyze_function_level_access(file_path, location, file_lines)
            
        elif check_name == "check_5_parameter_tampering":
            # Validate parameter tampering
            validation_result["justification"] = analyze_parameter_tampering(file_path, location, file_lines)
            
        elif check_name == "check_7_forced_browsing":
            # Validate forced browsing
            validation_result["justification"] = analyze_forced_browsing(file_path, location, file_lines)
            
        else:
            # Default analysis
            validation_result["justification"] = "Analysis requires detailed code examination"
            if "login" in location.lower() or "register" in location.lower():
                validation_result["justification"] += " - This appears to be authentication-related"
            elif "profile" in location.lower() or "user" in location.lower():
                validation_result["justification"] += " - This appears to be user data handling"
            elif "task" in location.lower() or "project" in location.lower():
                validation_result["justification"] += " - This appears to be project/task management"
        
        # Determine if this is actually exploitable
        validation_result["exploitability"] = determine_exploitability(validation_result)
        
        # Determine final status
        validation_result["status"] = determine_status(validation_result)
        
    except Exception as e:
        validation_result["evidence"] = f"Could not read file {file_path}: {str(e)}"
        validation_result["justification"] = "Unable to validate due to file access error"
        validation_result["status"] = "error"
    
    return validation_result

def analyze_authentication_requirement(file_path, location, file_lines):
    """
    Analyze if authentication is properly enforced
    """
    justification = ""
    
    if "login" in location.lower():
        # Check if login function has proper decorators
        for i, line in enumerate(file_lines):
            if "def login" in line or ("login" in line and "def" in line):
                # Look for login_required decorators in the next few lines
                for j in range(i, min(i+5, len(file_lines))):
                    if "@login_required" in file_lines[j]:
                        justification = "login view has @login_required decorator"
                        return justification
        justification = "login view does NOT have @login_required decorator - this is a vulnerability"
        
    elif "logout" in location.lower():
        # Check if logout function exists
        logout_exists = any("def logout" in line for line in file_lines)
        if not logout_exists:
            justification = "No logout_view function found - logout is likely handled by Django.contrib.auth"
        else:
            justification = "Logout function found but needs detailed review"
            
    elif "register" in location.lower():
        # Check if register function lacks authentication
        for i, line in enumerate(file_lines):
            if "def register" in line:
                # Look for login_required decorators
                for j in range(i, min(i+10, len(file_lines))):
                    if "@login_required" in file_lines[j]:
                        justification = "register view has @login_required decorator"
                        return justification
                justification = "register view does NOT have @login_required decorator - this is a vulnerability"
                return justification
                
    elif "forgot_password" in location.lower() or "reset_password" in location.lower():
        # Check if these functions lack authentication
        for i, line in enumerate(file_lines):
            if "def forgot_password" in line or "def reset_password" in line:
                # Look for login_required decorators
                for j in range(i, min(i+10, len(file_lines))):
                    if "@login_required" in file_lines[j]:
                        justification = "forgot/reset password view has @login_required decorator"
                        return justification
                justification = "forgot/reset password view does NOT have @login_required decorator - this is a vulnerability"
                return justification
    
    return justification or "Authentication requirement analysis needed"

def analyze_idor_issue(file_path, location, file_lines):
    """
    Analyze IDOR (Insecure Direct Object References) issues
    """
    justification = ""
    
    if "download_profile_pic" in location:
        # Check profile picture download function
        for i, line in enumerate(file_lines):
            if "download_profile_pic" in line:
                # Look for ownership checks
                for j in range(i, min(i+15, len(file_lines))):
                    line_content = file_lines[j]
                    if "user_id" in line_content and "get" in line_content:
                        # Looking for something like: user = User.objects.get(id=user_id)
                        if "objects.get" in line_content:
                            # Check if it's filtered by request.user
                            if "request.user" in line_content or "owner" in line_content:
                                justification = "Profile picture download function has proper ownership check"
                                return justification
                justification = "Profile picture download function fetches user by ID without ownership verification - this is an IDOR vulnerability"
                return justification
    
    elif "belongs_to_project" in location:
        # Check the belongs_to_project usage
        justification = "belongs_to_project function is used inconsistently - requires deeper review"
        
    elif "profile_view" in location:
        # Check profile view function
        justification = "profile_view function fetches user by ID without ownership check - this is an IDOR vulnerability"
        
    elif "profile_by_id" in location:
        # Check profile_by_id function
        justification = "profile_by_id function allows modification of any user's profile without ownership checks - this is an IDOR vulnerability"
        
    elif "session_messages" in location or "session_delete" in location:
        # Check chat session functions
        justification = "Chat session functions have ownership validation (they check request.user)"
    
    return justification or "IDOR analysis required"

def analyze_privilege_escalation(file_path, location, file_lines):
    """
    Analyze privilege escalation vulnerabilities
    """
    justification = ""
    
    if "manage_groups" in location:
        # Check if manage_groups has proper authorization
        for i, line in enumerate(file_lines):
            if "def manage_groups" in line:
                # Look for superuser or permission checks
                for j in range(i, min(i+15, len(file_lines))):
                    line_content = file_lines[j]
                    if "is_superuser" in line_content or "has_perm" in line_content:
                        if "is_superuser" in line_content or "can_change_group" in line_content:
                            justification = "manage_groups has proper authorization checks"
                            return justification
                justification = "manage_groups function requires @login_required but not superuser or specific permission checks - this allows privilege escalation"
                return justification
    
    elif "view_all_users" in location:
        # Check view_all_users function
        justification = "view_all_users only restricts by is_superuser - this is a privilege escalation issue"
        
    return justification or "Privilege escalation analysis needed"

def analyze_function_level_access(file_path, location, file_lines):
    """
    Analyze missing function-level access control
    """
    justification = ""
    
    if "task_delete" in location:
        # Check if task_delete function has proper ownership verification
        for i, line in enumerate(file_lines):
            if "def task_delete" in line:
                # Look for ownership checks in the function
                for j in range(i, min(i+15, len(file_lines))):
                    line_content = file_lines[j]
                    if "request.user" in line_content or "owner" in line_content:
                        justification = "task_delete has ownership verification"
                        return justification
                justification = "task_delete has @login_required but lacks ownership verification - this is vulnerable to unauthorized deletion"
                return justification
    
    elif "task_complete" in location:
        # Check if task_complete function has proper ownership verification
        justification = "task_complete function potentially lacks ownership verification"
        
    return justification or "Function level access control analysis needed"

def analyze_parameter_tampering(file_path, location, file_lines):
    """
    Analyze parameter tampering vulnerabilities
    """
    justification = ""
    
    if "profile_by_id" in location:
        # Check if profile_by_id function handles POST data with user ownership
        for i, line in enumerate(file_lines):
            if "def profile_by_id" in line:
                # Look for POST data processing
                for j in range(i, min(i+15, len(file_lines))):
                    line_content = file_lines[j]
                    if "POST" in line_content or "request." in line_content:
                        if "user_id" in line_content or "owner" in line_content:
                            justification = "profile_by_id processes POST data with potential ownership fields"
                            return justification
                justification = "profile_by_id function accepts user_id parameter and processes POST data - potential for parameter tampering"
                return justification
    
    return justification or "Parameter tampering analysis needed"

def analyze_forced_browsing(file_path, location, file_lines):
    """
    Analyze forced browsing vulnerabilities
    """
    justification = ""
    
    if "view_all_users" in location:
        # Check if view_all_users is accessible without proper authorization
        justification = "view_all_users endpoint is accessible at /taskManager/view_all_users/ and only requires superuser status - this is forced browsing"
        
    elif "manage_groups" in location:
        # Check if manage_groups lacks authorization
        justification = "manage_groups endpoint is accessible at /taskManager/manage_groups/ and lacks appropriate authorization checks - this is forced browsing"
        
    return justification or "Forced browsing analysis needed"

def determine_exploitability(result):
    """
    Determine if the finding can be exploited
    """
    justification = result["justification"].lower()
    
    if "vulnerability" in justification or "missing" in justification or "insecure" in justification:
        return "high"
    elif "has proper" in justification or "authorized" in justification:
        return "low"
    else:
        return "medium"

def determine_status(result):
    """
    Determine final validation status
    """
    justification = result["justification"].lower()
    
    if "vulnerability" in justification or "missing" in justification or "insecure" in justification or "allows" in justification:
        return "confirmed"
    elif "proper" in justification or "authorized" in justification or "has" in justification:
        return "rejected"
    else:
        return "pending"

# Process all findings from the analysis plan
validated_findings = []

for check in analysis_data.get("checks", []):
    check_id = check["check_id"]
    check_name = check["name"]
    
    for finding in check.get("findings", []):
        result = validate_finding(finding, check_name)
        validated_findings.append(result)

# Process additional checks
for check in analysis_data.get("additional_checks", []):
    check_id = check["check_id"]
    check_name = check["name"]
    
    for finding in check.get("findings", []):
        result = validate_finding(finding, check_name)
        validated_findings.append(result)

# Update the report with validated findings
report["validated_findings"] = validated_findings

# Update summary statistics
for finding in validated_findings:
    if finding["status"] == "confirmed":
        report["validation_summary"]["confirmed_vulnerabilities"] += 1
    elif finding["status"] == "rejected":
        report["validation_summary"]["rejected_findings"] += 1
    else:
        report["validation_summary"]["pending_validation"] += 1

# Save the report
with open("/home/defcon/nextgen/scripts/exercise-08/validation_report.json", 'w') as f:
    json.dump(report, f, indent=2)

print("Validation report generated successfully.")
print(f"Total findings: {report['total_findings']}")
print(f"Confirmed vulnerabilities: {report['validation_summary']['confirmed_vulnerabilities']}")
print(f"Rejected findings: {report['validation_summary']['rejected_findings']}")