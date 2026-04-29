from time import sleep
from pathlib import Path
from .llmProcessor import LLMProcessor


def extractBlocks(text):
    response_results = []
    change_text_results = []
    i = 0
    n = len(text)
    while i < n:
        # Check for \response{
        if text.startswith(r"\response{", i):
            start = i + len(r"\response{")
            content, new_index = extractNested(text, start)
            response_results.append(content)
            i = new_index
            continue
        # Check for \changeText{
        if text.startswith(r"\changeText{", i):
            start = i + len(r"\changeText{")
            content, new_index = extractNested(text, start)
            change_text_results.append(content)
            i = new_index
            continue
        i += 1
    return response_results, change_text_results


def extractNested(text, start_index):
    """Extract text until matching closing brace, handling nested braces."""
    stack = 1  # We already consumed the first '{'
    i = start_index
    while i < len(text):
        if text[i] == '{':
            stack += 1
        elif text[i] == '}':
            stack -= 1
            if stack == 0:
                return text[start_index:i], i + 1
        i += 1
    raise ValueError("Unmatched brace")


def processAndInvoke(llmProcessor:LLMProcessor, promptName:str, text:str, waitTime:int=0, attachFile=None) -> str:
    """ process LLM and invoke it and return content """
    sleep(waitTime)
    if attachFile is not None:
        with open(attachFile, 'r', encoding='utf-8') as fIn:
            context = '\n\nThe previous manuscript version was:\n'+fIn.read()+'\n\n'
    else:
        context = ''
    params = llmProcessor.processPrompt(promptName=promptName, selectedText =text.strip(), attachFilePath=attachFile)

    prompt = params['prompt']+context+params['selectedText']+ \
             ('\nOutput: return a valid latex string without any markdown formatting. When writing scientific '
              r'values use $0.1264\rm \mu m$ to include the unit.')
    result = params['runnable'].invoke(prompt, {'configurable': {'session_id': 'global'}})
    content = result.content if hasattr(result, 'content') else str(result)
    return content


initLatex = r"""\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{xcolor,soul}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage[normalem]{ulem}
\renewcommand{\familydefault}{\sfdefault}
\usepackage{graphicx}            % Include graphics
\usepackage{float}               % to control figure placement

% Define colors for clarity
\definecolor{reviewercolor}{rgb}{0.1,0.2,0.6} % blue for reviewers
\definecolor{responsecolor}{rgb}{0.0,0.0,0.0} % green for responses

% Commands for comments/responses
\newcommand{\reviewer}[1]{\vspace{0.3cm}\textcolor{reviewercolor}{\textbf{Reviewer:} #1}}
\newcommand{\editor}[1]{\vspace{0.3cm}\textcolor{reviewercolor}{\textbf{Editor:} #1}}
\newcommand{\response}[1]{\par\textcolor{responsecolor}{\textbf{Response:}} #1}
\newcommand{\changeText}[1]{\vspace*{-0.2cm}\begin{quote} \textcolor{responsecolor}{\hl{#1}}\end{quote}}

\begin{document}

\begin{center} {\LARGE \textbf{Rebuttal to Reviewer Comments}} \\
\vspace{0.3cm} %\textbf{Manuscript ID: XXXX-YYYY}
% \textbf{Title: `` ''}
\end{center}

\vspace{0.5cm}

\section*{Dear Editor, Dear Reviewers,}
We thank the reviewers and the editor for considering the manuscript and their very positive and constructive feedback. We have revised the manuscript accordingly and believe the changes have improved the clarity and quality of the paper. Below, we provide a detailed, point-by-point response to each comment, along with the changes in the manuscript. The manuscript itself contains the same changes.
\vspace{0.5cm}
"""

endLatex = r"""
\end{enumerate}

\vspace{0.5cm}
\section*{Closing Remarks}
We again thank the reviewers for their insightful comments and suggestions. We hope that the revisions adequately address all concerns.\\

With kind regards on behalf of the entire team\\
Steffen Brinckmann
\end{document}
"""