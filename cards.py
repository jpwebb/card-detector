""" This module contains functions and structures for processing playing card images """

### Import necessary packages
import cv2
import os
import copy
import numpy as np

from matplotlib import pyplot as plt

### Constants ###

# Card dimensions
CARD_MAX_AREA = 6000
CARD_MIN_AREA = 3500
CORNER_HEIGHT = 70
CORNER_WIDTH = 45
RANK_HEIGHT = 125
RANK_WIDTH = 70

# Polymetric approximation accuracy scaling factor
POLY_ACC_CONST = 0.01

# Card threshold level
CARD_THRESH = 200
RANK_THRESH = 30

### Structures ###

class card:
    """Structure to store information about cards in the camera image."""

    def __init__(self):
        self.contour = [] # Contour of card
        self.corner_pts = [] # Corner points of card
        self.center = [] # Center point of card
        self.img = [] # 200x300, flattened, grayed, blurred image
        self.rank_img = [] # Thresholded, sized image of card's rank
        self.best_rank_match = "Unknown" # Best matched rank
        self.rank_diff = 0 # Difference between rank image and best matched train rank image

class rank:
    """Structure to store information about each card rank."""

    def __init__(self):
        self.rank = "rank_name"
        self.img = [] # Thresholded image of card rank

### Functions ###

def get_card_contours(image):
    """ This function takes an images and returns a list of card objects with contour and corner info """

    # List to store card objects
    card_info = []

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)	

    # Gaussian blur
    blur = cv2.GaussianBlur(gray, (5,5), 0)

    cv2.imshow("Blurred playing area", blur)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # Use adaptive threshold or Otsu's method
    # Need to check if histogram is bimodal
    # https://docs.opencv.org/3.1.0/d7/d4d/tutorial_py_thresholding.html
    #plt.hist(image.ravel(),256,[0,256])
    #plt.show()
    thresh_level = CARD_THRESH
    
    # Threshold gaussian filtered image
    (_, thresh) = cv2.threshold(blur, thresh_level, 255, cv2.THRESH_BINARY)

    ### Debugging ###
    #cv2.imshow("Thresholded playing area", thresh); cv2.waitKey(0); cv2.destroyAllWindows()

    # Find contours and sort by size
    (_, cnts, hier) = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    index_sort = sorted(range(len(cnts)), key=lambda i : cv2.contourArea(cnts[i]),reverse=True)

    # Catch cases where no contours were detected
    try:

        # Initialize empty sorted contour and hierarchy lists
        cnts_sort = []
        hier_sort = []

        # Fill empty lists with sorted contour and sorted hierarchy. Now,
        # the indices of the contour list still correspond with those of
        # the hierarchy list. The hierarchy array can be used to check if
        # the contours have parents or not.
        for i in index_sort:
            cnts_sort.append(cnts[i])
            hier_sort.append(hier[0][i])  

        # Determine which of the contours are cards    
        for i in range(len(cnts_sort)):

            # Get the size of the cards
            size = cv2.contourArea(cnts_sort[i])

            # Use the perimeter of the card to set the accuracy parameter of
            # the polymetric approximation
            peri = cv2.arcLength(cnts_sort[i],True)
            accuracy = POLY_ACC_CONST*peri    

            # Approximate the shape of the contours            
            approx = cv2.approxPolyDP(cnts_sort[i], accuracy, True)

            # Cards are determined to have an area within a given range,
            # have 4 corners and have no parents
            if ((size < CARD_MAX_AREA) and (size > CARD_MIN_AREA) 
                and (len(approx) == 4) and (hier_sort[i][3] == -1)):                
                new_card = card()
                new_card.contour = cnts_sort[i]  
                new_card.corner_pts = np.float32(approx)

                # Add the new card to the list
                card_info.append(new_card)
                
                ### Debugging ###
                """
                print('size = {}, acc = {}, numCorners = {}'.format(size, accuracy, len(approx)))
                temp_img = copy.deepcopy(image)
                cv2.drawContours(temp_img, cnts_sort, i, (0,255,0), 3)
                cv2.imshow("This Card Contour", temp_img); cv2.waitKey(0); cv2.destroyAllWindows()  
                """

    # If there are no contours, do nothing
    except:
        pass

    return card_info

def process_card(this_card, image):
    """ This function takes an image and contour associated with a card and returns a top-down image of the card """

    # Find width and height of card's bounding rectangle
    x, y, w, h = cv2.boundingRect(this_card.contour)
    this_card.width, this_card.height = w, h

    # Find the centre of the card
    pts = this_card.corner_pts
    average = np.sum(pts, axis=0)/len(pts)
    cent_x = int(average[0][0])
    cent_y = int(average[0][1])
    this_card.center = [cent_x, cent_y]

    # Create a flattened image of the isolated card
    this_card.img = flattener(image, pts, w, h)

    cv2.imshow("This card flattened", this_card.img); cv2.waitKey(0); cv2.destroyAllWindows()

    # Crop the corner from the card
    rank_img = this_card.img[0:CORNER_HEIGHT, 0:CORNER_WIDTH]
    #cv2.imshow("This rank", rank_img); cv2.waitKey(0); cv2.destroyAllWindows()

    # Thresholding using Otsu's method
    #plt.hist(rank_img.ravel(),256,[0,256]); plt.show() # Check if the image is bimodal
    (_, thresh) = cv2.threshold(rank_img, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    cv2.imshow("This card thresholded", thresh); cv2.waitKey(0); cv2.destroyAllWindows()

    # Find the largest contour
    (_, this_rank_cnts, _) = cv2.findContours(thresh, cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    this_rank_cnts = sorted(this_rank_cnts, key=cv2.contourArea,reverse=True)

    # Get the bounding box around the rank, and resize to the template size
    if len(this_rank_cnts) != 0:
        x1,y1,w1,h1 = cv2.boundingRect(this_rank_cnts[0])
        rank_crop = thresh[y1:y1+h1, x1:x1+w1]
        this_card.rank_img = cv2.resize(rank_crop, (RANK_WIDTH,RANK_HEIGHT), 0, 0)        

    return this_card

def get_card_rank(card_img):
    """ This function returns the best rank match of a given card image """
    

    
    return rank_image, rank_match, match_score

def load_ranks(path):
    """ Load rank images from a specified path. Store rank images in a list of rank objects """

    ranks = []
    rank_names = ['Ace', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Jack', 'Queen', 'King']

    for name in rank_names:

        # Create a new instance of the rank class
        new_rank = rank()

        # Store information about the current rank
        img_path = os.path.join(path, name+'.jpg')
        new_rank.img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        new_rank.rank = name

        # Add to the list
        ranks.append(new_rank)

    return ranks

def flattener(image, pts, w, h):
    """Flattens an image of a card into a top-down 200x300 perspective.
    Returns the flattened, re-sized, grayed image.
    See www.pyimagesearch.com/2014/08/25/4-point-opencv-getperspective-transform-example/"""
    temp_rect = np.zeros((4,2), dtype = "float32")
    
    s = np.sum(pts, axis = 2)

    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]

    diff = np.diff(pts, axis = -1)
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]

    # Need to create an array listing points in order of
    # [top left, top right, bottom right, bottom left]
    # before doing the perspective transform

    if w <= 0.8*h: # If card is vertically oriented
        temp_rect[0] = tl
        temp_rect[1] = tr
        temp_rect[2] = br
        temp_rect[3] = bl

    if w >= 1.2*h: # If card is horizontally oriented
        temp_rect[0] = bl
        temp_rect[1] = tl
        temp_rect[2] = tr
        temp_rect[3] = br

    # If the card is 'diamond' oriented, a different algorithm
    # has to be used to identify which point is top left, top right
    # bottom left, and bottom right.
    
    if w > 0.8*h and w < 1.2*h: #If card is diamond oriented
        # If furthest left point is higher than furthest right point,
        # card is tilted to the left.
        if pts[1][0][1] <= pts[3][0][1]:
            # If card is titled to the left, approxPolyDP returns points
            # in this order: top right, top left, bottom left, bottom right
            temp_rect[0] = pts[1][0] # Top left
            temp_rect[1] = pts[0][0] # Top right
            temp_rect[2] = pts[3][0] # Bottom right
            temp_rect[3] = pts[2][0] # Bottom left

        # If furthest left point is lower than furthest right point,
        # card is tilted to the right
        if pts[1][0][1] > pts[3][0][1]:
            # If card is titled to the right, approxPolyDP returns points
            # in this order: top left, bottom left, bottom right, top right
            temp_rect[0] = pts[0][0] # Top left
            temp_rect[1] = pts[3][0] # Top right
            temp_rect[2] = pts[2][0] # Bottom right
            temp_rect[3] = pts[1][0] # Bottom left     
        
    maxWidth = 200
    maxHeight = 300

    # Create destination array, calculate perspective transform matrix,
    # and warp card image
    dst = np.array([[0,0],[maxWidth-1,0],[maxWidth-1,maxHeight-1],[0, maxHeight-1]], np.float32)
    M = cv2.getPerspectiveTransform(temp_rect,dst)
    warp = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    warp = cv2.cvtColor(warp,cv2.COLOR_BGR2GRAY)        

    return warp