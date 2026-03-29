# WhisperTunnel Book-Style Report

This folder contains a book-format LaTeX report for the WhisperTunnel VPN codebase.

## Structure

- `main.tex`: Main document (front matter, TOC, chapter includes)
- `chapters/*.tex`: Core technical chapters
- `appendices/*.tex`: Command and configuration appendices
- `figures/`: Placeholders for screenshots and diagrams

## Build

From this directory:

```bash
make
```

If successful, output will be:

- `whispertunnel-report.pdf`

## Notes

- The report uses a Times-like professional serif style (`newtxtext/newtxmath`) and is formatted in a book layout.
- Figures include placeholder blocks so you can drop in screenshots later without changing chapter flow.
- Suggested placeholders to replace:
  - Codebase tree screenshot
  - Namespace topology diagram
  - Packet capture snapshots
  - TUN interface and route snapshots
