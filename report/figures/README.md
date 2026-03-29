# Figure Inventory

The report uses **mixed diagram approach**: 4 TikZ-generated diagrams + 2 user-provided screenshots.

## Generated Diagrams (TikZ) ✅

These are auto-generated in LaTeX with `tikz` package and render natively in PDF:

1. Figure `2.1` (`report/chapters/02_background.tex`)
   - **Content**: Network namespace topology (veth pair, tunnel interfaces)
   - **Status**: ✅ Complete

2. Figure `4.1` (`report/chapters/04_system_architecture.tex`)
   - **Content**: Client/Server stacks with bidirectional encrypted flow
   - **Status**: ✅ Complete

3. Figure `5.1` (`report/chapters/05_protocol_and_crypto.tex`)
   - **Content**: Authentication handshake sequence diagram
   - **Status**: ✅ Complete

4. Figure `7.1` (`report/chapters/07_deployment_and_operations.tex`)
   - **Content**: NAT and iptables forwarding rules visualization
   - **Status**: ✅ Complete

## User-Provided Screenshots ⏳

Provide PNG files for the following placeholders:

5. Figure `3.1` (`report/chapters/03_codebase_overview.tex`)
   - **Content**: Codebase/module structure visualization
   - **Suggestion**: Use `tree` output, IDE file structure, or architecture diagram
   - **File**: `codebase-snapshot.png`

6. Figure `6.1` (`report/chapters/06_implementation_walkthrough.tex`)
   - **Content**: Runtime terminal output, process metrics, or execution demo
   - **Suggestion**: Screenshot from `demo.sh` execution, metrics dashboard, or process logs
   - **File**: `runtime-snapshot.png`

## Removed placeholders

The following requested placeholders are removed from the build:

- Figure `1.1`
- Figure `8.1`
- Figure `9.1`
- Figure `10.1`
- Figure `11.1`

If you keep the suggested filenames above in this folder, replacing placeholders later will be straightforward.
