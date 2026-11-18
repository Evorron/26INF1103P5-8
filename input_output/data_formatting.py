import textwrap


class DataFormatting:
    def __init__(self, widths: list[int]):
        """Initialize with the column widths calculated for the table."""
        self.widths = widths

    def format_row(self, values: list[str]) -> list[str]:
        ##Format a row, wrapping long text
        wrapped = [
            textwrap.wrap(str(v), width=self.widths[i], break_long_words=True, break_on_hyphens=False) or [""]
            for i, v in enumerate(values)
        ]
        row_height = max(len(lines) for lines in wrapped)

        formatted_lines = []
        for line_index in range(row_height):
            cells = [
                lines[line_index].rjust(self.widths[i]) if i in (2, 3, 4) else lines[line_index].ljust(self.widths[i])
                if line_index < len(lines) else "".ljust(self.widths[i])
                for i, lines in enumerate(wrapped)
            ]
            ##Format for data display table
            formatted_lines.append("| " + " | ".join(cells) + " |")
        return formatted_lines

    def format_table(self, headers: list[str], rows: list[list[str]]) -> None:
        """Print the complete formatted table with borders."""
        border = "+" + "+".join("-" * (w + 2) for w in self.widths) + "+"

        print("\nMatching records")
        print(border)
        for line in self.format_row(headers):
            print(line)
        print(border)
        for row in rows:
            for line in self.format_row(row):
                print(line)
            print(border)
        print("\n")