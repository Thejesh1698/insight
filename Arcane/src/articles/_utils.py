
def truncate_text_to_token_limit(text, encoder, token_limit):

    def is_under_limit(index):
        # Use the provided function to calculate tokens for the substring
        return len(encoder.encode(text[:index])) <= token_limit

    if len(encoder.encode(text)) <= token_limit:  # if the whole text is under the token limit
        return text

    left, right = 0, len(text)
    valid_limit = 0  # index of the last valid token position
    # Binary search to find the token limit
    while left <= right:
        mid = (left + right) // 2
        if is_under_limit(mid):
            valid_limit = mid
            left = mid + 1
        else:
            right = mid - 1
    # Find the last space before the valid_limit to ensure we're at a word boundary
    space_index = text.rfind(' ', 0, valid_limit)
    if space_index == -1:
        # If there's no space, we've hit the start of the text
        return text[:valid_limit]  # Return up to the valid limit even if mid-word

    return text[:space_index]
