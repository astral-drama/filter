# Code Refactoring Prompt

You are refactoring code in the **{{ project_name }}** project to improve maintainability and performance.

## Project Information

- **Project**: {{ project_name }}
- **Path**: {{ project_path }}
- **Target Branch**: {{ branch_name | default("main") }}
- **Refactoring Scope**: {{ refactor_scope | default("TBD") }}

## Refactoring Goals

{{ refactoring_goals | default("Improve code quality, maintainability, and performance") }}

## Areas of Focus

{{ focus_areas | default("- Code duplication\n- Performance bottlenecks\n- Complex functions\n- Outdated patterns") }}

## Refactoring Strategy

1. **Assessment**:
   - Analyze current code structure
   - Identify code smells and technical debt
   - Review performance metrics if available
   - Document current behavior to preserve

2. **Planning**:
   - Break refactoring into manageable chunks
   - Prioritize high-impact, low-risk changes
   - Plan for backward compatibility if needed

3. **Implementation**:
   - Extract reusable functions/modules
   - Simplify complex logic
   - Improve naming and documentation
   - Optimize performance bottlenecks
   - Follow {{ coding_standards | default("project coding standards") }}

4. **Validation**:
   - Run comprehensive test suite
   - Verify no behavioral changes
   - Check performance improvements
   - Update documentation

## Technical Constraints

- **Language**: {{ language | default("Auto-detect") }}
- **Framework**: {{ framework | default("Auto-detect") }}
- **Compatibility**: {{ compatibility_requirements | default("Maintain current API") }}
- **Performance**: {{ performance_targets | default("No degradation") }}

## Safety Measures

- [ ] All tests pass before starting
- [ ] Frequent small commits
- [ ] Comprehensive testing after each change
- [ ] Performance benchmarking (if applicable)
- [ ] Code review ready

## Deliverables

- [ ] Refactored code with improved structure
- [ ] Updated tests
- [ ] Performance measurements (if applicable)
- [ ] Updated documentation
- [ ] Migration guide (if breaking changes)

---

**Important**: Preserve all existing functionality while improving code quality.