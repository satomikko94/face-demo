import os
import simplejson
from flask import Flask, render_template, redirect, url_for, request, make_response
from flask import send_from_directory
from werkzeug import secure_filename

import argparse
import base64

from PIL import Image
from PIL import ImageDraw

from googleapiclient import discovery
import httplib2
from oauth2client.client import GoogleCredentials


ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/home/stackato/app/upfile'
app.debug = True

# [START get_vision_service]
DISCOVERY_URL='https://{api}.googleapis.com/$discovery/rest?version={apiVersion}'


def get_vision_service():
    credentials = GoogleCredentials.get_application_default()
    return discovery.build('vision', 'v1', credentials=credentials,
                           discoveryServiceUrl=DISCOVERY_URL)
# [END get_vision_service]


@app.route("/")
def index():
    return render_template('index.html')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        max_results = request.form.get['faces']
        if file and allowed_file(file.filename):
            input_filename = app.config['UPLOAD_FOLDER'] + "/" + secure_filename(file.filename)
            output_filename = app.config['UPLOAD_FOLDER'] + "/out_" + secure_filename(file.filename)
            file.save(input_filename)
            return redirect(url_for('main', input_filename=input_filename, output_filename=output_filename, max_results=max_results))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''

@app.route('/detect/<input_filename>')
# [START main]
def main(input_filename, output_filename, max_results):
    with open(input_filename, 'rb') as image:
        faces = detect_face(image, max_results)
#        print('Found %s face%s' % (len(faces), '' if len(faces) == 1 else 's'))

#        print('Writing to file %s' % output_filename)
        # Reset the file pointer, so we can read the file again
        image.seek(0)
        highlight_faces(image, faces, output_filename)
    return render_template('show_results.html', input_filename=input_filename, output_filename=output_filename, faces=faces)

# [END main]


# [START detect_face]
def detect_face(face_file, max_results=4):
    """Uses the Vision API to detect faces in the given file.

    Args:
        face_file: A file-like object containing an image with faces.

    Returns:
        An array of dicts with information about the faces in the picture.
    """
    image_content = face_file.read()
    batch_request = [{
        'image': {
            'content': base64.b64encode(image_content).decode('UTF-8')
            },
        'features': [{
            'type': 'FACE_DETECTION',
            'maxResults': max_results,
            }]
        }]

    service = get_vision_service()
    request = service.images().annotate(body={
        'requests': batch_request,
        })
    response = request.execute()

    return response['responses'][0]['faceAnnotations']
# [END detect_face]


# [START highlight_faces]
def highlight_faces(image, faces, output_filename):
    """Draws a polygon around the faces, then saves to output_filename.

    Args:
      image: a file containing the image with the faces.
      faces: a list of faces found in the file. This should be in the format
          returned by the Vision API.
      output_filename: the name of the image file to be created, where the faces
          have polygons drawn around them.
    """
    im = Image.open(image)
    draw = ImageDraw.Draw(im)

    for face in faces:
        box = [(v.get('x', 0.0), v.get('y', 0.0)) for v in face['fdBoundingPoly']['vertices']]
        draw.line(box + [box[0]], width=5, fill='#00ff00')

    del draw
    return im.save(output_filename)
# [END highlight_faces]


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
