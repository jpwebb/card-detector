""" This program takes an image of a blackjack playing surface and identifies the cards """

### Import necessary packages
import os
import cv2
import copy
import cards

### Constants
rank_path = "card_images"
font = cv2.FONT_HERSHEY_SIMPLEX

### Main code body

# Load the card rank images into a list of rank objects
ranks = cards.load_ranks(rank_path)

# Get next image of playing area
img = cv2.imread(os.path.join('game_images', 'transformed_small1.png'))
img_disp = copy.deepcopy(img)

# Get a list of all of the contours around cards
all_cards = cards.findCards(img)

for i in range(len(all_cards)):

    # Produce a top-down image of each card
    all_cards[i].processCard(img)

    # Find the best rank match for this card
    all_cards[i].matchRank(ranks, cards.TEMPLATE_MATCHING)

     # Draw on the temporary image
    if all_cards[i].best_rank_match == "Unknown":
        cnt_col = cards.RED
    else:
        cnt_col = cards.GREEN
    
    cv2.drawContours(img_disp, [all_cards[i].contour], 0, cnt_col, 2)
    text_pos = (all_cards[i].center[0]-20, all_cards[i].center[1])
    cv2.putText(img_disp, all_cards[i].best_rank_match, text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.7, cards.MAGENTA, 2, cv2.LINE_AA)

# Show the display image
cv2.imshow("Detected Cards", img_disp); cv2.waitKey(0); cv2.destroyAllWindows()
