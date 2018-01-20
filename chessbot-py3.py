import re
import time
import chess.pgn
from stockfishpy import *
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException


def load_page():
    driver = webdriver.Firefox()
    driver.get('https://www.chess.com/login')
    return driver


def login(driver, username, password):
    elem = driver.find_element_by_id('username')
    elem.clear()
    elem.send_keys(username)
    elem = driver.find_element_by_id('password')
    elem.clear()
    elem.send_keys(password)
    elem.send_keys(Keys.RETURN)
    return


def start_play(driver):
    while driver.current_url != "https://www.chess.com/live":
        driver.get('https://www.chess.com/live')

    print(driver.current_url)

    try:
        myElem = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'game-over-dialog')))
        elem = driver.find_element(By.CLASS_NAME, 'game-over-dialog')
        elem = elem.find_element_by_class_name('icon-x')
        elem.click()
        elem = driver.find_element(By.CLASS_NAME, 'tab-nav-challenge')
        elem.click()
    except TimeoutException:
        print("Unable to close Popup!")

    try:
        myElem = WebDriverWait(driver, 3).until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, ".quick-challenge > div:nth-child(3) > button:nth-child(1)")))
        print("Game Started!")
    except TimeoutException:
        print("Loading took too much time!")

    button = driver.find_element(By.CSS_SELECTOR, ".quick-challenge > div:nth-child(3) > button:nth-child(1)")
    button.click()

    return


def get_user_color(driver, username):
    while (1):
        try:
            myElem = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'notification-game-new-game-playing')))
            print("User Color Detected!")
            break
        except TimeoutException:
            print("Searching for Opponent!")

    elem = driver.find_element(By.CLASS_NAME, "notification-game-new-game-playing")
    print(elem.text)
    players = re.findall(r'(\w+)\s\(\d+\)', elem.text)

    white_player = players[0]
    black_player = players[1]

    if white_player == username:
        print(username + ' is white')
        return "white"
    else:
        print(username + ' is black')
        return "black"


def pgn_generator(driver, move_number, pgn, user_color):
    move_id = "movelist_" + str(move_number)
    move_notation = ""
    print(move_id)
    while (1):
        try:
            myElem = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, move_id)))
            print("Move Made!")
            break
        except TimeoutException:
            print("Opponent is thinking!")
    while move_notation == "":
        move_notation = driver.find_element_by_id(move_id).find_element_by_class_name('gotomove').text
    print(move_notation)

    driver.execute_script("""
         document.getElementById("highlight1").remove();
         document.getElementById("highlight2").remove();
    """)

    if move_number % 2 == 1:
        pgn += str(move_number // 2 + 1) + "." + move_notation + " "
    else:
        pgn += move_notation + " "
    return pgn, move_notation


def get_best_move(chessEngine):
    pgnfilename = str('pgn.pgn')

    with open(pgnfilename) as f:
        game = chess.pgn.read_game(f)

    game = game.end()
    board = game.board()

    chessEngine.ucinewgame()
    chessEngine.setposition(board.fen())

    move = chessEngine.bestmove()
    print(move['bestmove'])

    bestmove = move['bestmove']
    return bestmove


def highlight_move(driver, user_color, best_move):
    driver.execute_script("""
        element = document.getElementsByClassName('chessboard')[0];
        x = element.style.width.replace(/\D/g,'') / 8;

        chessboard_id = document.getElementsByClassName('chessboard')[0].id + '_boardarea';

        if(arguments[4].localeCompare("white") == 0){
            var from_position_coordinate = [(arguments[0].charCodeAt(0) - 97) * x, (8 - parseInt(arguments[1])) * x];
            var to_position_coordinate = [(arguments[2].charCodeAt(0) - 97) * x, (8 - parseInt(arguments[3])) * x];
        }
        else{
            var from_position_coordinate = [(7 - (arguments[0].charCodeAt(0) - 97)) * x, (parseInt(arguments[1]) - 1) * x];
            var to_position_coordinate = [(7 - (arguments[2].charCodeAt(0) - 97)) * x, (parseInt(arguments[3]) - 1) * x];
        }


        var pos_old = "position: absolute; z-index: 2; pointer-events: none; opacity: 0.9; background-color: rgb(244, 42, 50); width:" + x + "px; height: " + x + "px; transform: translate(" + from_position_coordinate[0] + "px," +  from_position_coordinate[1] + "px);";
        var pos_new = "position: absolute; z-index: 2; pointer-events: none; opacity: 0.9; background-color: rgb(244, 42, 50); width:" + x + "px; height: " + x + "px; transform: translate(" + to_position_coordinate[0] + "px," +  to_position_coordinate[1] + "px);";

        element = document.createElement('div');            
        element.setAttribute("id", "highlight1");    
        element.setAttribute("style", pos_old);    
        document.getElementById(chessboard_id).appendChild(element);

        element = document.createElement('div');
        element.setAttribute("id", "highlight2");            
        element.setAttribute("style", pos_new); 
        document.getElementById(chessboard_id).appendChild(element);
       """, best_move[0], best_move[1], best_move[2], best_move[3], user_color)
    return


def auto_move(driver):
    element = driver.find_element(By.XPATH, '//*[@id="highlight1"]')
    element.click()
    # ActionChains(driver).move_to_element_with_offset(element, 0, 2).click().perform();

    element = driver.find_element(By.XPATH, '//*[@id="highlight2"]')
    element.click()
    # ActionChains(driver).move_to_element_with_offset(element, 0, 2).click().perform();

    # driver.execute_script("""
    #     document.getElementById('highlight1').click();
    #     document.getElementById('highlight2').click();
    # """)
    return


def play_game(driver, user_color, chessEngine):
    pgn = ""
    # Clear pgn.pgn file before use
    open('pgn.pgn', 'w').close()

    highlight_move(driver, user_color, "e2e4")
    auto_move(driver)

    for move_number in range(1, 500):
        pgn, move_notation = pgn_generator(driver, move_number, pgn, user_color)

        print(pgn)

        with open("pgn.pgn", "w") as text_file:
            text_file.write("%s" % pgn)

        best_move = get_best_move(chessEngine)

        highlight_move(driver, user_color, best_move)

        auto_move(driver)

        if game_end(user_color, move_notation) == 1:
            return
    return


def game_end(user_color, move_notation):
    if user_color == 'white':
        if move_notation == '1-0':
            print('User Won!')
            return 1
        elif move_notation == '0-1':
            print('User Lost!')
            return 1
        elif move_notation == '1-1':
            print('Game drawn!')
            return 1
    else:
        if move_notation == '0-1':
            print('User Won!')
            return 1
        elif move_notation == '1-0':
            print('User Lost!')
            return 1
        elif move_notation == '1-1':
            print('Game drawn!')
            return 1

    return 0


def new_game(driver, username, chessEngine):
    start_play(driver)
    user_color = get_user_color(driver, username)
    play_game(driver, user_color, chessEngine)
    return


def main():
    driver = load_page()

    chessEngine = Engine('./stockfish_8_x64', param={'Threads': 5, 'Ponder': None})

    username = ''
    password = ''

    login(driver, username, password)
    time.sleep(3)

    while (1):
        new_game(driver, username, chessEngine)

        print("Play Again? (y/n)")
        play_again = input()

        if (play_again != 'y'):
            break

    driver.close()


main()
