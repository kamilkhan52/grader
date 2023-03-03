# This python program helps log scores and comments for an assignment being graded. The program will read a list of student names from a file, and then prompt the user for a score and comment for each student. The program will then write the scores and comments to a file.


# TODO
# Allow the option to add multiple comments for a single subquestion. If the comment and deduction is followed by a + symbol, then the comment will be added to the list of comments for that subquestion. 

import pandas as pd
import pickle
import os
from datetime import datetime
import argparse
import signal

# if CTRL-C is pressed
def signal_handler(sig, frame):
    print("\n\n\nCTRL-C pressed. Saving state...")
    save_state()
    print(f"Saved state to {grading_id}/saved_state.pkl. \n Total students graded: {students_done}/{len(student_names)}\nYou can resume grading by providing the same grading ID ({grading_id}).")
    exit(0)

signal.signal(signal.SIGINT, signal_handler) # register signal handler

# parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('--names', type=str, required=True, help='csv file containing student names in the first column')
parser.add_argument('--output', type=str, required=False, help='output filename', default='scores')
args = parser.parse_args()

# Function to get the student names from a CSV file


def get_student_names(file_path):
    # read the file into a pandas dataframe (file has no header row)
    print(f"Reading student names from {file_path}. If you want to use a different file, please edit the file path in the code.")
    df = pd.read_csv(file_path, header=None)
    return df.iloc[:, 0].tolist()

# Function to initialize the scores dictionary


def init_scores_and_comment_history(student_names, num_questions, num_subquestions):
    points_lost = {}
    comment_history = {}
    for student_name in student_names:
        points_lost[student_name] = {}
        for i in range(num_questions):
            question = f"Q{i + 1}"
            points_lost[student_name][question] = {f"{chr(j)}": 0 for j in range(97, 97 + num_subquestions[i])}

    # initialze comment history
    for i in range(num_questions):
        q = f"Q{i + 1}"
        comment_history[q] = {}
        for sq in [chr(j) for j in range(97, 97 + num_subquestions[i])]:
            comment_history[q][sq] = []

    return points_lost, comment_history

def grade_subquestion(question, subquestion):
    """
    Grades a subquestion and returns the and comments and number of points lost.
    """
    global comment_history
    if subquestion not in comment_history[question]:
        comment_history[question][subquestion] = []

    # Display previous comments as options
    options = {}
    for i, (comment, deduction) in enumerate(comment_history[question][subquestion]):
        options[str(i+1)] = (comment, deduction)
        print(f"{i+1}. {comment} (-{deduction})")

    # Add new comment option
    new_option_num = len(comment_history[question][subquestion]) + 1
    new_option = f"{new_option_num}. Add new comment"
    options[str(new_option_num)] = new_option

    print(new_option)

    # Get user choice and handle new comment
    # New: If choice is ended by a + symbol, then the comment will be added to the list of comments for that subquestion.
    while True:
        choice = input("Select an option: ")
        # skip if choice is empty
        if not choice:
            return "None", 0 # no comment entered (this will not be saved into output file)

        if choice in options:
            if choice == str(new_option_num):
                comment_and_deduction = input("Enter new comment and deduction (comment, deduction): ")
                while True:
                    try:
                        comment, deduction = comment_and_deduction.rsplit(',', 1)
                        break
                    except ValueError:
                        print("Invalid input. Please try again.")
                        comment_and_deduction = input("Enter new comment and deduction (comment, deduction): ")

                deduction = int(deduction)
                if deduction < 0:
                    print(f"Converting negative deduction ({deduction}) to positive ({-deduction}).")
                    deduction = -deduction
                comment_history[question][subquestion].append((comment, deduction))
                return comment, deduction
            else:
                return options[choice][0], options[choice][1]
        else:
            print("Invalid choice. Please try again.")


def record_scores(question, subquestions, student_name, points_lost):
    for subquestion in subquestions:
        print(f"{question}{subquestion}:")
        comment, deduction = grade_subquestion(question, subquestion)
        points_lost[student_name][question][subquestion] = (comment, deduction)

    return points_lost[student_name][question]

def save_state():
    """
    Saves the current state of the grading process to a pickle file.
    """
    global out_filename # output filename needs to be global so it can be accessed by final print statement
    global students_done

    state = [grading_id, student_names, students_done, num_questions, num_subquestions, max_score, points_lost, comment_history, INPUT_FILE, OUTPUT_FILE]

    with open(f"{grading_id}/saved_state.pkl", 'wb') as f:
        pickle.dump(state, f)
    # get current timestamp as valid string for filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_filename = f"{grading_id}/{OUTPUT_FILE}_{timestamp}.csv"
    with open(out_filename, "w") as out:
        out.write("Student Name,Total Score,Points Lost,Comments")
        for student_name in student_names:
            total_points_lost = 0
            comments = ""
            for i in range(num_questions):
                question = f"Q{i + 1}"
                for j in range(num_subquestions[i]):
                    subquestion = f"{chr(j + 97)}"
                    if not isinstance(points_lost[student_name][question][subquestion], tuple):  # no comment entered
                        continue
                    if points_lost[student_name][question][subquestion][1] != 0: # points lost
                        total_points_lost += points_lost[student_name][question][subquestion][1]
                        comments += f"{question}{subquestion}: {points_lost[student_name][question][subquestion][0]} (-{points_lost[student_name][question][subquestion][1]})\n"
                    elif points_lost[student_name][question][subquestion][0] != "None": # no points lost (just comment, but not None (when Return is pressed))
                        comments += f"{question}{subquestion}: {points_lost[student_name][question][subquestion][0]}\n"

            out.write(f'\n"{student_name}","{max_score - total_points_lost}","{total_points_lost}","{comments.strip()}"')


def load_state(grading_id):
    try:
        with open(f"{grading_id}/saved_state.pkl", 'rb') as f:
            state = pickle.load(f)
    except FileNotFoundError:
        print("No saved state found. Exiting...")
        exit()
    print("Loaded state:")
    # print each element in state with string indicating variable name

    print(f"grading_id:{state[0]}\nstudents_done: {state[2]}\nnum_questions: {state[3]}\nnum_subquestions: {state[4]}\nmax_score: {state[5]}\nINPUT_FILE: {state[-2]}\nOUTPUT_FILE: {state[-1]}\n")

    return state

# grading identifier to keep track of progress
grading_id = input("Enter unique grading ID for this assignment (for example ECE452_HW3): ")
students_done = 0

if os.path.isdir(grading_id):
    print(f"{grading_id} exists. Loading saved state...")
    grading_id, student_names, students_done, num_questions, num_subquestions, max_score, points_lost, comment_history, INPUT_FILE, OUTPUT_FILE = load_state(grading_id)
else:
    print(f"{grading_id} does not exist. Creating new session...")
    os.mkdir(grading_id)
    # set constants for the input file and output file
    INPUT_FILE = args.names # student names file
    OUTPUT_FILE = 'scores'  # will be appended with timestamp

    # read the student names from the input file
    student_names = get_student_names(INPUT_FILE)
    # get the number of questions and subquestions
    num_questions = int(input("Enter the number of questions: "))
    num_subquestions = []
    for i in range(num_questions):
        num_subquestions.append(int(input(f"Enter the number of subquestions for question {i + 1}: ")))

    # get the max score for the assignment
    max_score = int(input("Enter the max score: "))
    # initialize the scores dictionary
    points_lost, comment_history = init_scores_and_comment_history(student_names, num_questions, num_subquestions)


for i, student_name in enumerate(student_names):
    if i < students_done:
        continue
    print(f"\n\n\n\n -------------- Scoring {student_name} ({i + 1}/{len(student_names)}) -------------- ")
    # loop through each question and subquestion, and prompt the user to enter scores
    for q_no in range(num_questions):
        question = f"Q{q_no + 1}"
        # Determine the list of subquestions based on the number of subquestions for the current question
        start = ord('a')  # ASCII value for 'a'
        end = start + num_subquestions[q_no]
        subquestions = [chr(j) for j in range(start, end)]
        grade_summary = record_scores(question, subquestions, student_name, points_lost)
        print(f"Grade summary for {student_name} for {question}: {grade_summary}")
        students_done=i
    save_state()

print("Scores saved to", out_filename)
