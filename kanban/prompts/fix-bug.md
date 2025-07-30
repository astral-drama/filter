# Bug Fix Prompt

You are debugging and fixing an issue in the **{{ project_name }}** project.

## Bug Information

- **Project**: {{ project_name }}
- **Location**: {{ project_path }}
- **Branch**: {{ branch_name | default("main") }}
- **Bug ID**: {{ bug_id | default("N/A") }}
- **Priority**: {{ priority | default("Medium") }}

## Bug Description

{{ bug_description | default("Please refer to the issue description for bug details.") }}

## Steps to Reproduce

{{ reproduction_steps | default("1. TBD - Add reproduction steps") }}

## Expected Behavior

{{ expected_behavior | default("Describe what should happen instead") }}

## Debugging Approach

1. **Investigate**: 
   - Reproduce the issue locally
   - Examine relevant code sections
   - Check logs and error messages
   - Review recent changes that might have introduced the bug

2. **Analyze**:
   - Identify root cause
   - Consider impact of potential fixes
   - Plan minimal, targeted solution

3. **Fix**:
   - Implement the fix with proper error handling
   - Add logging to help prevent similar issues
   - Ensure fix doesn't break existing functionality

4. **Test**:
   - Verify the fix resolves the issue
   - Run existing test suite
   - Add regression tests if appropriate

## Environment Details

- **OS**: {{ os_type | default("Linux") }}
- **Runtime**: {{ runtime_version | default("Latest") }}
- **Dependencies**: Check project's dependency files

## Checklist

- [ ] Bug reproduced locally
- [ ] Root cause identified
- [ ] Fix implemented
- [ ] Tests updated/added
- [ ] Manual testing completed
- [ ] No regressions introduced

---

**Remember**: Work methodically and document your findings as you debug.