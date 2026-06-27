# Third-Party Attribution

This project ports algorithms and test fixtures from
[microsoft/markitdown](https://github.com/microsoft/markitdown), licensed
under the MIT License. This project does **not** depend on the `markitdown`
package at runtime; the following specific pieces of code and data were
adapted from or copied out of that repository:

- `app/converters/pdf_converter.py` — the PDF form/table detection algorithm
  and MasterFormat partial-numbering merge logic are ported from
  `packages/markitdown/src/markitdown/converters/_pdf_converter.py`.
- `app/converters/markdown_utils.py` — `CustomMarkdownify` is ported from
  `packages/markitdown/src/markitdown/converters/_markdownify.py`.
- `tests/fixtures/test.pdf`, `tests/fixtures/test.docx`,
  `tests/fixtures/SPARSE-2024-INV-1234_borderless_table.pdf`,
  `tests/fixtures/masterformat_partial_numbering.pdf` — test fixtures copied
  from `packages/markitdown/tests/test_files/`.

## MIT License (microsoft/markitdown)

    MIT License

    Copyright (c) Microsoft Corporation.

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
