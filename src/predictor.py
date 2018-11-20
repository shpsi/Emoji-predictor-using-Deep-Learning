import os
import sys
import cv2
import time
import logging
import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt
import glob
import tqdm

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))
import src
from src.model import model

config = tf.ConfigProto()
config.gpu_options.allow_growth = True


def softmax(x):
    """Compute softmax values for each sets of scores in x."""
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()


def inference(sess, gray_img_input):
    
    img = gray_img_input.reshape(1, 48, 48, 1).astype(float) / 255
    
    y_c = sess.run(y_conv, feed_dict={X:img, keep_prob:1.0})
    
    y_c = softmax(y_c)
    p = np.argmax(y_c, axis=1)
    score = np.max(y_c)
    logger.debug('''softmax-out: {}, 
        predicted-index: {}, 
        predicted-emoji: {}, 
        confidence: {}'''.format(y_c, p[0], index_emo[p[0]], score))
    return p[0], score
        

def from_cam(sess):
    cap = cv2.VideoCapture(0)

    face_cascade = cv2.CascadeClassifier('G:/VENVIRONMENT/computer_vision/Lib/site-packages/cv2/data/haarcascade_frontalface_default.xml')

    font               = cv2.FONT_HERSHEY_SIMPLEX
    fontScale          = 1
    fontColor          = (255,255,255)
    lineType           = 2

    while True:
        # Capture frame-by-frame
        ret, frame = cap.read()

        # Operations on the frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # detect the faces, bounding boxes
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        # draw the rectangle (bounding-boxes)
        for (x,y,w,h) in faces:
            cv2.rectangle(frame, (x,y), (x+w, y+h), (255,0,0), 2)
            bottomLeftCornerOfText = (x+10,y+h+10)

            face_img_gray = gray[y:y+h, x:x+w]
            face_img_gray = cv2.resize(face_img_gray, (48, 48))
            s = time.time()
            p, confidence = inference(sess, face_img_gray)
            logger.critical('model inference time: {}'.format(time.time() - s))
            
            if confidence > 0.45:
            
                img2 = emoji_to_pic[index_emo[p]]
                img2 = cv2.resize(img2, (w, h))

                alpha = img2[:,:,3]/255.0

                frame[y:y+h, x:x+w, 0] = frame[y:y+h, x:x+w, 0] * (1-alpha) + alpha * img2[:,:,0]
                frame[y:y+h, x:x+w, 1] = frame[y:y+h, x:x+w, 1] * (1-alpha) + alpha * img2[:,:,1]
                frame[y:y+h, x:x+w, 2] = frame[y:y+h, x:x+w, 2] * (1-alpha) + alpha * img2[:,:,2]

                cv2.putText(frame,f'Confidence: {confidence}', 
                            bottomLeftCornerOfText, 
                            font, 
                            fontScale,
                            fontColor,
                            lineType)

            else: 
                cv2.putText(frame,'NEUTRAL', 
                            bottomLeftCornerOfText, 
                            font, 
                            fontScale,
                            fontColor,
                            lineType)

        # Display the resulting frame
        cv2.imshow('gray-scale', gray)
        cv2.imshow('faces', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':

    logger = logging.getLogger('emojifier.predictor')
    CHECKPOINT_SAVE_PATH = os.path.join(os.path.dirname(__file__), os.pardir, 'model_checkpoints')
    EMOJI_FILE_PATH = os.path.join(os.path.dirname(__file__), os.pardir, 'emoji')
    tf.reset_default_graph()
    
    emo_index = {'smile': 0,'kiss': 1,'tease': 2,'angry': 3,'glass': 4}
    index_emo = {v:k for k,v in emo_index.items()}
    
    emoji_to_pic = {
    'smile': None,'kiss': None,'tease': None,'angry': None,'glass': None
    }

    # ATTENTION: CHANGE THE '\\' A/C TO YOUR OS
    files = glob.glob(EMOJI_FILE_PATH + '\\*.png')

    logger.info('loading the emoji png files in memory ...')
    for file in tqdm.tqdm(files):
        logger.debug('file path: {}'.format(file))
        # ATTENTION: CHANGE THE '\\' A/C TO YOUR OS
        emoji_to_pic[file.split('\\')[-1].split('.')[0]] = cv2.imread(file, -1)

    X = tf.placeholder(
        tf.float32, shape=[None, 48, 48, 1]
    )
    
    keep_prob = tf.placeholder(tf.float32)

    y_conv = model(X, keep_prob)
    
    saver = tf.train.Saver()
    
    with tf.Session(config=config) as sess:
        saver.restore(sess, os.path.join(CHECKPOINT_SAVE_PATH, 'model.ckpt'))

        logger.info('Opening the camera for getting the video feed ...')
        from_cam(sess)
