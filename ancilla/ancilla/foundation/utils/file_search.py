'''
 file_search.py
 utils

 Created by Kevin Musselman (kevin@frenzylabs.com) on 02/18/20
 Copyright 2019 FrenzyLabs, LLC.
'''


import re, os


def find_start_end(fp, regex):
    if regex and type(regex) == str:
      regex = re.compile(regex)
    start_pos = find_start(fp, regex)
    if start_pos < 0:
        return None
    end_pos = find_end(fp, regex)
    return (start_pos, end_pos)

def find_start(fp, regex=None):
    start_pos = -1

    while True:
        cur_pos = fp.tell()
        line = fp.readline()
        if not line:
            return start_pos
        if not regex:
          return cur_pos
        elif regex.search(line):
            print(f"Start Regex success = {line}")
            start_pos = cur_pos
            return start_pos
        

def find_end(fp, regex):
    end_pos = -1
    
    linegen = reverse_readline(fp)
    while True:
        pos, line = next(linegen)                
        if not line:
            print("NO LINE")
            return end_pos    
        if not regex:
          return pos
        elif regex.search(line):
            print(f"End Regex success {pos} = {line}")
            end_pos = pos
            return end_pos

def reverse_readline(fh, buf_size=8192):
    """A generator that returns the lines of a file in reverse order"""

    segment = None
    offset = 0
    fh.seek(0, os.SEEK_END)
    file_size = remaining_size = fh.tell()
    while remaining_size > 0:
        offset = min(file_size, offset + buf_size)
        seekpos = file_size - offset
        fh.seek(seekpos)
        buffer = fh.read(min(remaining_size, buf_size))
        remaining_size -= buf_size
        lines = buffer.split('\n')
        # The first line of the buffer is probably not a complete line so
        # we'll save it and append it to the last line of the next buffer
        # we read
        linepos = seekpos + len(buffer)
        if segment is not None:
            # If the previous chunk starts right from the beginning of line
            # do not concat the segment to the last line of new chunk.
            # Instead, yield the segment first 
            if buffer[-1] != '\n':
                lines[-1] += segment
            else:
                yield (linepos, segment)
        segment = lines[0]
        
        for index in range(len(lines) - 1, 0, -1):
            if lines[index]:
                linepos -= len(lines[index])
                yield (linepos, lines[index])
    # Don't yield None if the file was empty
    if segment is not None:
        yield (0, segment)