import re
import time
import chess.pgn
from stockfishpy import Engine
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

# Configure these values before starting the program
username = ''
password = ''
play_bongcloud = False
auto_play = False
auto_start_new_game = False

def load_page():
    driver = webdriver.Firefox()
    driver.get('https://www.chess.com/login')
    return driver


def login(driver):
    global username, password
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
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'upgrade-modal')))
        elem = driver.find_element(By.CLASS_NAME, 'upgrade-modal')
        elem = elem.find_element_by_xpath('/html/body/div[1]/div[4]/div/div[2]/div[2]/span')
        elem.click()
        elem = driver.find_element(By.CLASS_NAME, 'tab-nav-challenge')
        elem.click()
    except TimeoutException:
        pass

    button = driver.find_element(By.CSS_SELECTOR, ".form-button-component")
    button.click()

    return


def get_user_color(driver):
    while (1):
        try:
            myElem = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'draw-button-component')))
            break
        except TimeoutException:
            print("Waiting for user to start the game..")

    elem_list = driver.find_elements_by_class_name("chat-message-component")

    if('warn-message-component' in elem_list[-1].get_attribute('class')):
        elem = elem_list[-2]
    else:
        elem = elem_list[-1]

    print(elem.text)
    
    players = re.findall(r'(\w+)\s\(\d+\)', elem.text)

    white_player = players[0]

    global username

    if white_player == username:
        print(username + ' is white')
        return "white"
    else:
        print(username + ' is black')
        return "black"


def pgn_generator(driver, move_number, pgn, user_color):
    last_move = ''

    while (1):
        try:
            elements = driver.find_elements_by_class_name('move-text-component')
            if(len(elements) >= move_number):
                last_move = elements[move_number-1].text.strip()
                break
        except TimeoutException:
            print("Opponent is thinking!")

    if move_number % 2 == 1:
        pgn += str(move_number // 2 + 1) + "." + last_move + " "
    else:
        pgn += last_move + " "
    return pgn, last_move


def get_best_move(chessEngine):
    pgnfilename = str('pgn.pgn')

    with open(pgnfilename) as f:
        game = chess.pgn.read_game(f)

    game = game.end()
    board = game.board()

    chessEngine.ucinewgame()
    chessEngine.setposition(board.fen())

    move = chessEngine.bestmove()
    bestmove = move['bestmove']

    return bestmove


def highlight_move(driver, user_color, best_move):
    driver.execute_script("""
        chessboard = document.getElementById('game-board');
        x = chessboard.style.width.replace(/\D/g,'') / 8;

        if(arguments[4].localeCompare("white") == 0){
            var from_position_coordinate = [(arguments[0].charCodeAt(0) - 97) * x, (8 - parseInt(arguments[1])) * x];
            var to_position_coordinate = [(arguments[2].charCodeAt(0) - 97) * x, (8 - parseInt(arguments[3])) * x];
        }
        else{
            var from_position_coordinate = [(7 - (arguments[0].charCodeAt(0) - 97)) * x, (parseInt(arguments[1]) - 1) * x];
            var to_position_coordinate = [(7 - (arguments[2].charCodeAt(0) - 97)) * x, (parseInt(arguments[3]) - 1) * x];
        }

        highlight1_pos = arguments[0].charCodeAt() - 'a'.charCodeAt() + 1 
        highlight1_class = '0' + highlight1_pos + '0' + arguments[1];
        element = document.createElement('div');            
        element.setAttribute("id", "highlight1");
        element.setAttribute("class", "square square-" + highlight1_class + " marked-square");        
        element.setAttribute("style", "background-color: rgb(244, 42, 50); opacity: 0.9");    
        chessboard.appendChild(element);

        highlight2_pos = arguments[2].charCodeAt() - 'a'.charCodeAt() + 1
        highlight2_class = '0' + highlight2_pos + '0' + arguments[3];
        element = document.createElement('div');
        element.setAttribute("id", "highlight2");            
        element.setAttribute("class", "square square-" + highlight2_class + " marked-square");        

        element.setAttribute("style", "background-color: rgb(244, 42, 50); opacity: 0.9");    
        chessboard.appendChild(element);
       """, best_move[0], best_move[1], best_move[2], best_move[3], user_color)
    return


def auto_move(driver):
    element = driver.find_element(By.XPATH, '//*[@id="highlight1"]')
    ActionChains(driver).move_to_element_with_offset(element, 0, 2).click().perform()
    time.sleep(0.05)
    element = driver.find_element(By.XPATH, '//*[@id="highlight2"]')
    ActionChains(driver).move_to_element_with_offset(element, 0, 2).click().perform()
    return


def play_game(driver, user_color, chessEngine):
    global auto_play

    pgn = ""
    # Clear pgn.pgn file before use
    open('pgn.pgn', 'w').close()

    gameOverMessageCount = 0
    elements = driver.find_elements_by_class_name('chat-message-component')
    for element in elements:
        if element.get_attribute('data-notification') == 'gameOver':
            gameOverMessageCount += 1 


    if user_color == 'white':
        highlight_move(driver, user_color, 'e2e4')
        if auto_play:
            auto_move(driver)

    for move_number in range(1, 500):
        pgn, move_notation = pgn_generator(driver, move_number, pgn, user_color)

        with open("pgn.pgn", "w") as text_file:
            text_file.write("%s" % pgn)

        game_ended = game_end(driver, gameOverMessageCount)

        if game_ended or move_notation[-1] == '#':
            print(pgn)
            print('Game finished!')
            return

        best_move = get_best_move(chessEngine)

        if play_bongcloud:
            if user_color == 'white' and move_number == 2:
                best_move = 'e1e2'
            if user_color == 'black':
                if move_number == 1:
                    best_move = 'e7e5'
                if move_number == 3:
                    best_move = 'e8e7'

        try_count = 0
        while try_count < 3:
            try:
                if((user_color == 'white' and move_number % 2 == 0) or (user_color == 'black' and move_number % 2 == 1)):
                    highlight_move(driver, user_color, best_move)
                    if auto_play:
                        auto_move(driver)
                break
            except:
                print('Failed to highlight square')

            try_count = try_count + 1
            time.sleep(0.5)
    return


def game_end(driver, gameOverMessageCount):
    game_finished_message = 0

    gameOverMessageCountNew = 0

    elements = driver.find_elements_by_class_name('chat-message-component')
    for element in elements:
        if element.get_attribute('data-notification') == 'gameOver':
            gameOverMessageCountNew += 1
            
    if gameOverMessageCountNew > gameOverMessageCount:
        game_finished_message = 1
        
    return game_finished_message


def new_game(driver, chessEngine):
    global auto_start_new_game

    if(auto_start_new_game):
        start_play(driver)

    user_color = get_user_color(driver)
    play_game(driver, user_color, chessEngine)
    return


def main():
    driver = load_page()
    chessEngine = Engine('./stockfish_8_x64', param={'Threads': 10, 'Ponder': None})

    login(driver)
    time.sleep(3)

    while (1):
        new_game(driver, chessEngine)
        time.sleep(3)

    driver.close()


main()
