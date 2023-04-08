# This python program helps log scores and comments for an assignment being graded. The program will read a list of student names from a file, and then prompt the user for a score and comment for each student. The program will then write the scores and comments to a file.


# TODO
# Allow the option to add multiple comments for a single subquestion. If the comment and deduction is followed by a + symbol, then the comment will be added to the list of comments for that subquestion.
# Print total points lost for each student at the end of grading.

import pandas as pd
import pickle
import os
from datetime import datetime
import argparse
import signal

# if CTRL-C is pressed


def signal_handler(sig, frame):
    print("\n\n\nCTRL-C pressed.")
    if students_done == 0:
        print(f"No students graded. No state to save.")
        exit(0)
    print("Saving state...")
    save_state()
    print(f"Saved state to {grading_id}/saved_state.pkl. \n Total students graded: {students_done}/{len(student_names)}\nYou can resume grading by providing the same grading ID ({grading_id}).")
    exit(0)


signal.signal(signal.SIGINT, signal_handler)  # register signal handler

# parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('--names', type=str, required=True, help='csv file containing student names in the first column')
parser.add_argument('--solutions_file', type=str, required=True, help='text file containing solutions')
parser.add_argument('--output', type=str, required=False, help='output filename', default='scores')
args = parser.parse_args()

# Function to get the student names from a CSV file


def get_student_names(file_path):
    # read the file into a pandas dataframe (file has no header row)
    print(f"Reading student names from {file_path}...")
    df = pd.read_csv(file_path, header=None)
    return df.iloc[:, 0].tolist()


def get_solutions(solutions_file):
    solutions = {}
    print(f"Reading solutions from {solutions_file}...")
    with open(solutions_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if len(line.split(":")) != 4:
                print(f"Invalid line in solutions file: {line}")
                continue
            question, subquestion, total_points, answer = line.split(":")
            question = "Q" + question
            if question not in solutions:
                solutions[question] = {}
            solutions[question][subquestion] = (int(total_points), answer)
    return solutions


def init_scores_and_comment_history(student_names, num_questions, num_subquestions):
    points_lost = {}
    comment_history = {}
    for student_name in student_names:
        points_lost[student_name] = {}
        for i in range(num_questions):
            question = f"Q{i + 1}"
            points_lost[student_name][question] = {f"{chr(j)}": [] for j in range(97, 97 + num_subquestions[i])}

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
        choices = input("Select options (comma-separated): ")
        # skip if choice is empty
        if not choices:
            return [("None", 0)]  # no comment entered (this will not be saved into output file)

        choices = choices.split(",")
        comments = []
        for choice in choices:
            if choice in options:
                if choice == str(new_option_num):
                    comment_and_deduction = input("Enter new comment and deduction (comment, deduction): ")
                    while True:
                        try:
                            comment, deduction = comment_and_deduction.rsplit(',', 1)
                            if "\"" in comment:
                                comment = comment.replace("\"", "")
                                print(f"Removed quotes from comment: {comment}")
                            break
                        except ValueError:
                            print("Invalid input. Please try again.")
                            comment_and_deduction = input("Enter new comment and deduction (comment, deduction): ")

                    deduction = int(deduction)
                    if deduction < 0:
                        print(f"Converting negative deduction ({deduction}) to positive ({-deduction}).")
                        deduction = -deduction
                    comment_history[question][subquestion].append((comment, deduction))
                    comments.append((comment, deduction))
                else:
                    deduction = options[choice][1]
                    comment = options[choice][0].replace("\"", "")
                    comments.append((comment, deduction))
            else:
                print("Invalid choice. Please try again.")
                continue

        # comment = "\n".join([str(c[0]) for c in comments])
        # tot_deduction = sum([c[1] for c in comments])
        return comments


def record_scores(question, subquestions, student_name, points_lost):
    for subquestion in subquestions:
        if len(solutions):  # if solutions are provided, then print the correct answer
            print(f"\n\n{question}{subquestion}: ({solutions[question][subquestion][0]}) Answer: {solutions[question][subquestion][1]}\n")
        else:
            print(f"\n\n{question}{subquestion}:")

        comments = grade_subquestion(question, subquestion)

        for comment, deduction in comments:
            points_lost[student_name][question][subquestion].append((comment, deduction))

    return points_lost[student_name][question]


def save_state():
    """
    Saves the current state of the grading process to a pickle file.
    """
    global out_filename  # output filename needs to be global so it can be accessed by final print statement
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
                    if not len(points_lost[student_name][question][subquestion]):  # no comment entered
                        continue
                    for comment, deduction in points_lost[student_name][question][subquestion]:
                        if deduction != 0:  # points lost
                            total_points_lost += deduction
                            comments += f"{question}{subquestion}: {comment} (-{deduction})\n"
                        elif comment != "None":  # no points lost (just comment, but not None (when Return is pressed))
                            comments += f"{question}{subquestion}: {comment}\n"

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


def get_student_score(student_name):
    total_points_lost = 0
    for i in range(num_questions):
        question = f"Q{i + 1}"
        for j in range(num_subquestions[i]):
            subquestion = f"{chr(j + 97)}"
            if not len(points_lost[student_name][question][subquestion]):  # no comment entered
                continue
            for _, deduction in points_lost[student_name][question][subquestion]:
                if deduction != 0:  # points lost
                    total_points_lost += deduction

    return max_score - total_points_lost


# grading identifier to keep track of progress
grading_id = input("Enter unique grading ID for this assignment (for example ECE452_HW3): ")
students_done = 0

if os.path.isdir(grading_id):
    print(f"{grading_id} exists. Loading saved state...")
    grading_id, student_names, students_done, num_questions, num_subquestions, max_score, points_lost, comment_history, INPUT_FILE, OUTPUT_FILE = load_state(grading_id)
else:
    print(f"Creating new session: {grading_id}")
    os.mkdir(grading_id)
    # set constants for the input file and output file
    INPUT_FILE = args.names  # student names file
    OUTPUT_FILE = 'scores'  # will be appended with timestamp

    # read the student names from the input file
    student_names = get_student_names(INPUT_FILE)

solutions = {}  # will always read from solutions file even when resuming grading to allow for updates to solutions file
if args.solutions_file is not None:
    SOLUTIONS_FILE = args.solutions_file
    solutions = get_solutions(SOLUTIONS_FILE)

    # get the number of questions and subquestions from solutions dictionary
    num_questions = len(solutions)
    num_subquestions = []
    for question in solutions:
        num_subquestions.append(len(solutions[question]))
else:
    num_questions = int(input("Enter the number of questions: "))
    num_subquestions = []
    for i in range(num_questions):
        num_subquestions.append(int(input(f"Enter the number of subquestions for question {i + 1}: ")))


# get the max score for the assignment
max_score = int(input("Enter the max score: "))

# initialize the scores dictionary
points_lost, comment_history = init_scores_and_comment_history(student_names, num_questions, num_subquestions)


for i, student_name in enumerate(student_names):
    if i <= students_done:
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
        students_done = i
    # print total score for student
    total_score = get_student_score(student_name)
    print(f"Total score for {student_name}: {total_score}/{max_score}")
    save_state()

print("Scores saved to", out_filename)
