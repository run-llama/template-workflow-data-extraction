# Copy Utils Enhancement Notes

## Current `fix_template` Analysis

The current `fix_template` command works by:
1. Taking a git revision as input
2. Finding files in `test-proj/` that changed since that revision 
3. For non-jinja files: copying them back to template structure
4. For jinja files: showing warnings with diffs that need manual resolution

### Problems with Current Approach

1. **Manual revision specification**: User must know/remember what revision to compare against
2. **Limited diff context**: Only shows what changed in materialized files, not what the template would generate
3. **No actual conflict resolution**: Warns about jinja files but doesn't help resolve them
4. **No verification of template correctness**: Doesn't check if template changes would actually produce the desired materialized output

## Enhancement Proposals

### 1. Auto-detect merge base with main (default revision)

**Implementation**: 
```python
def get_default_revision(script_dir: Path) -> str:
    """Get merge base with main as default revision."""
    try:
        result = run_git_command(["git", "merge-base", "HEAD", "main"], cwd=script_dir)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        # Fallback to main if merge-base fails
        return "main"
```

**Benefits**: Eliminates need to manually specify revision in most cases

### 2. Three-way merge approach

The real insight here is that we need to compare THREE states:
- **A**: Template at base revision → materialized 
- **B**: Current template → materialized (what template would generate now)
- **C**: Current materialized files in test-proj

**Current approach**: Only looks at C vs A
**Better approach**: Compare B vs C to find actual discrepancies

### 3. Generate "expected" materialized view for comparison

**Key insight**: Instead of just looking at git history, we should:

1. **Generate a fresh materialized copy** from current template (call it `expected-proj/`)
2. **Compare `expected-proj/` vs `test-proj/`** to find real discrepancies
3. **Only warn about actual differences** that need resolution

**Implementation outline**:
```python
def compare_with_expected_materialized(script_dir: Path) -> None:
    """Compare current test-proj with freshly generated template."""
    
    # Generate expected materialized version in temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        expected_proj = Path(temp_dir) / "expected-proj"
        
        copier.run_copy(
            src_path=str(script_dir),
            dst_path=str(expected_proj),
            data={"project_name": "test-proj", "project_title": "Test Project"},
            unsafe=True,
        )
        
        # Compare expected vs actual
        compare_directories(expected_proj, script_dir / "test-proj")
```

### 4. Smart jinja conflict resolution

For jinja files that differ, we could:

1. **Show the actual template content** that would be generated
2. **Highlight specific lines** that differ between expected and actual
3. **Suggest template changes** by reverse-engineering from materialized changes

**Example flow**:
```
Found difference in test-proj/pyproject.toml:
  Expected (from template): name = "test-proj" 
  Actual (in test-proj):    name = "my-awesome-proj"
  
  Template file: pyproject.toml.jinja
  Suggested change: name = "{{ project_name }}" → name = "{{ project_title }}"
```

## Do we even need the revision?

**Short answer**: Not for the main use case.

**Analysis**:
- The revision was useful when we only looked at git history
- With the "expected materialized" approach, we compare current template output vs current test-proj
- Revision might still be useful for incremental workflows ("only check files I touched recently")

**Recommendation**: 
- Make revision optional, defaulting to full comparison
- Keep revision option for power users who want incremental checks

## Proposed New Command Structure

```bash
# Compare all files (most common case)
./copy_utils.py fix_template

# Compare only files changed since specific revision  
./copy_utils.py fix_template --since=HEAD~3

# Auto-detect merge base with main
./copy_utils.py fix_template --since=auto
```

## Implementation Priority

1. **High**: Generate expected materialized comparison (eliminates false positives)
2. **Medium**: Auto-detect merge base as default
3. **Low**: Smart jinja conflict resolution (complex, may not be worth it)

The "expected materialized" approach addresses the core issue: distinguishing between intentional changes and template drift. 