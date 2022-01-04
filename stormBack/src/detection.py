import cv2
from datetime import datetime
import time
import sys
import os

BASE_INTER_FRAME_DELAY = 0.002 #delay between each frame. An increased delay means slower motion in the video
SLOMO_INTER_FRAME_DELAY = 0.02 #delay between each frame. An increased delay means slower motion in the video
AROUND_LIGHTNING_FRAMES = 10 #delay in seconds to let before the lightning to smoother the clip (and not get the flash right at video opening)
BRIGHTNESS_TOLERANCE_VALUE = 1100 # used arbitrarily, it seems to detect quite nicely the thunder for the video it was tested on
HSV_MAX_TOLERANCE = 100 #brightest point of the picture. Had false negative at 10.10 mean value and 130 max value so try to tweek it with max values
HSV_MEAN_VALUE = 55

MEAN_MARGIN = 0.8
TENDANCIAL_MEAN_NB_VALUES = 50
LI_CAN_RADIUS = 10
LI_CAN_SENSI = 10
LI_CAN_ACTIVE = True

#####TODO Write the thunder peak intensity in the extracted video name. Same for photos.
#####TODO Séléction des éclairs (l'image LA PLUS brillante ?), stockage de leur path en bdd (pour le tweeter ultérieurement ?) > StormPoster

#####TODO Séléction des éclairs (l'image LA PLUS brillante ?), stockage de leur path en bdd (pour le tweeter ultérieurement ?) > StormPoster
## show the nb_sequences number increasing with lightnings detected.
## when not playing, let the user be able to change sensibility (BRIGHTNESS_TOLERANCE_VALUE) on a slider or such.
## let the user able to set minimal sequence duration. If no such video quantity avail, fill with black

def my_int_cast(str):
    if bool(str):
        return int(str)
    else:
        return 0

def return_err(msg, code):
    print(msg)
    return code

def extract_clips(path, params):
    print(f"[Detection.py][extract_clips() started] path = {path}")
    # get the video flux
    cap = cv2.VideoCapture(path)
    if (cap.isOpened() == False):
        return return_err(f"Error, failed to open {path} video", 1)

    brightest_frames = []
    #FIRST RUN SHOULD BE USED TO COMPUTE THE AVERAGE LUMINOSITY OF THE SCENE
    #
    frames_to_extract = process_video(cap, params, brightest_frames)
    print(f"frames to extract before polish {frames_to_extract}")
    #Clip is 1 sequence itself + the discontinuities
    frames_to_extract = polish_the_thunder(frames_to_extract)
    print(f"frames to extract after polish {frames_to_extract}")
    nb_sequences = 1 + check_discontinuities(frames_to_extract)

    print(f"[{nb_sequences}] sequences to handle")
    #done to reset the iterator if the videocapture object
    cap.release()
    cap = cv2.VideoCapture(path)
    #pass again the video to extract to determined images
    frame_extraction(path, params, cap, frames_to_extract, nb_sequences, brightest_frames)
    print(f"fte{frames_to_extract}, len fte {len(frames_to_extract)}\n nbseq {nb_sequences}, brightest_frames {brightest_frames}")
    cap.release()
    cv2.destroyAllWindows()
    return

def check_discontinuities(lst):
    if (len(lst) < 1):
        return 0
    disc = 0

    for i, val in enumerate(lst):
        # if next elem - current elem != 1, they are not consecutive
        if i + 1 < len(lst) :
            if lst[i + 1] - lst[i] != 1:
                print()
                disc += 1
    return disc

def range_it_up(n):
    res = range(n - AROUND_LIGHTNING_FRAMES, n + AROUND_LIGHTNING_FRAMES + 1)
    ret = []
    for i in res:
        ret.append(i)
    return ret

# this is garbage for now == fucks out my sequence count number by changing the order in the list AND adding negative values at its end.
def polish_the_thunder(frames_to_extract):
    res = map(range_it_up, frames_to_extract)
    flat_list = [item for sublist in res for item in sublist]
    return list(set(flat_list))

def frame_extraction(path, params, cap, frames_to_extract, nb_sequences, brightest_frames):
    vw, vh, vfps = int(cap.get(3)), int(cap.get(4)), cap.get(cv2.CAP_PROP_FPS)
    outputs = []

    print(f"{os.path.dirname(path)}")
    output_dirname = f"{os.path.dirname(path)}/output-{datetime.now().replace(microsecond=0)}"
    try:
        #codec for the videoWriter object
        fourcc = cv2.VideoWriter_fourcc(*'DIVX')
        for i in range(nb_sequences):
            outfoldername = f"{output_dirname}/thunder-{i}"
            os.makedirs(outfoldername)
            outputs.append(cv2.VideoWriter(f"{outfoldername}/thunder.avi", fourcc, vfps, (vw, vh)))
    except:
        return_err(f"Oops! {sys.exc_info()[0]} occurred.", 1)

    frameIndex, seq_nb = 0, 0
    print(f"Starting extract job with {frames_to_extract}")
    while True:
        ret, frame = cap.read()
        if ret is False:
            print("No more frames to grab. Closing")
            break

        print(f"analyzing [{seq_nb}]")
        if frameIndex in frames_to_extract:
            outputs[seq_nb].write(frame)
            print(f"Wrote {frameIndex} frame in {outputs[seq_nb]}")
            if frameIndex+1 not in frames_to_extract:
                seq_nb += 1

        ## TODO Rewrite brightest_frames logic to find the visible thunders

        if frameIndex in brightest_frames:
            print(f"Saving {output_dirname}/thunder-{seq_nb}/thunder-{frameIndex}.jpeg")
            try:
                cv2.imwrite(f"{output_dirname}/thunder-{seq_nb}/thunder-{frameIndex}.jpeg", frame)
            except:
                print("Oops!", sys.exc_info()[0], "occurred.")

        frameIndex += 1

    for i in range(nb_sequences):
        print(f"releasing {i} - {outputs[i]}")
        outputs[i].release()

    # save the parameters used to generate the output
    with open(f"{output_dirname}/extract_params.txt", 'w') as f:
        print(f"{params}", file=f)

def kill_process():
    sys.exit("User killed process")
    quit()

def mypystack_push(stack, element):
    stack.append(element)
    stack.pop(0)

def process_video(cap, params, brightest_frames):
    index, extracted_frames = [0, 0]
    frames_to_extract = []
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    tendencial_mean = 0.0
    mean_list = []

    while True:
        ret, frame = cap.read()
        if ret is False:
            print("No more frames to grab. Closing")
            break
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        hsv_mean, hsv_max, hsv_min = hsv[...,2].mean(), hsv[...,2].max(), hsv[...,2].min()
        delay = my_int_cast((params.get('BASE_INTER_FRAME_DELAY')))/100000
#        time.sleep(delay or BASE_INTER_FRAME_DELAY)

        # or hsv_max > HSV_MAX_TOLERANCE // TOO SENSIBLE
        param_BTV = my_int_cast(params.get('BRIGHTNESS_TOLERANCE_VALUE'))
        param_BTV = param_BTV or BRIGHTNESS_TOLERANCE_VALUE
#        print(f"params {param_BTV} ")

        # TODO VERIFY THAT (MEAN + VALUE) / 2.0 === means.append(hsv_mean); [means] / len(means)
        # if (hsv_mean > param_BTV /100):
        #index > TENDANCIAL_MEAN_NB_VALUES and
        if hsv_mean > (tendencial_mean + MEAN_MARGIN):
            print(f"THUNDER !!!frameidx {hsv_mean} > {(tendencial_mean + MEAN_MARGIN)} --at  {index}/{frame_count} \n\
                 trendsmean {tendencial_mean} HSV mean {hsv_mean}     min {hsv_min}       max {hsv_max}")
            frames_to_extract.append(index) #could be replaced by THE ACTUAL FRAME stocked in videoSTREAM to finally ultimately write it
            extracted_frames += 1
            param_HMV = my_int_cast(params.get('HSV_MEAN_VALUE'))
            param_HMV = param_HMV or HSV_MEAN_VALUE
            if hsv_mean > param_HMV:
                brightest_frames.append(index)
                print(f"Adding {index} with {hsv_mean}")

            slomo_delay = my_int_cast((params.get('SLOMO_INTER_FRAME_DELAY')))/10000
#            time.sleep(slomo_delay or SLOMO_INTER_FRAME_DELAY)
        else:
            print(f"frameidx {index}/{frame_count} ({(index/frame_count)*100} / 100) --\n\
              trendsmean {tendencial_mean} HSV_mean {hsv_mean}  min {hsv_min}   max {hsv_max}")

        # le calcul de cette moyenne peut être trop sensible. En effet
        # nous basons la moyenne sur moy(t1) + moy_img(t) / 2.0. De ce fait, nous ne basons pas la moyenne
        # sur une longue séquence, pourrait générer faux négatifs lors de séquences d'éclair longues (donc pic de la moyenne construite sur temps court)
        tendencial_mean += hsv_mean
        if (index < TENDANCIAL_MEAN_NB_VALUES):
            mean_list.append(hsv_mean)
        else:
            mypystack_push(mean_list, hsv_mean)

        tendencial_mean = sum(mean_list) / len(mean_list)

        if (params and params.get('show_processing')):
            cv2.imshow("Thunder", frame)

        # KEYBOARD INPUT HANDLING
        key = cv2.waitKey(2)
        if key == 27:
            print("Escaped")
            kill_process()
            break
        # PAUSE logic
        if key == ord(' '):
            print("PAUSED")
            cv2.waitKey(-1) #wait until any key is pressed

        index += 1

    return frames_to_extract

def detection(path, params):
    print(f"\n\n[DETECTION.PY] >> Called main with args {path} params = [{params}]")
    # videopath = "../data/VID_20210620_012302.mp4"
    extract_clips(path, params)


if __name__ == "__main__":
    detection()
