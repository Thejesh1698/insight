import re


class SummaryService:

    @staticmethod
    def validate_summary_format(s):

        # check based on number of words
        num_words = len([x for x in s.strip().replace('\n', '').split(' ') if x != ''])
        if not 10 < num_words < 150:
            return False

        # Split the string based on <br> and strip each resulting string
        points = [point.strip() for point in s.split('<br>') if point.strip()]

        # Check if the number of points is 2 or 3
        if len(points) not in [2, 3, 4, 5]:
            return False

        for point in points:
            # Extracting label and actual point content
            label_match = re.match(r"^(\*\*[^*]+\*\*):?\s*", point)
            if not label_match:
                return False
            label = label_match.group(0)
            actual_point = point[len(label):].lstrip()  # Strip leading spaces from the point part

            # Checking if the actual point content contains asterisks or <strong> tags
            if '*' in actual_point or '<strong>' in actual_point or '</strong>' in actual_point:
                return False
        # If all checks pass
        return True

    @staticmethod
    def convert_markdown_to_html(markdown_summary):
        # Split the text by <br> to process each line separately
        lines = markdown_summary.split("<br>")
        html_lines = []

        for line in lines:
            # Convert bold text (e.g., **text**) to strong tags (e.g., <strong>text</strong>)
            bolded_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)

            # Add the processed line to the list of HTML lines
            html_lines.append(bolded_text.strip())

        # Join the HTML lines with <br> tags to maintain the structure
        html_text = '<br>'.join(html_lines)
        return html_text
