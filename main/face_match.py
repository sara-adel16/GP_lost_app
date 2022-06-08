import face_recognition

unknown_image = face_recognition.load_image_file( 'C:/Users/YourPc/python face reco/face_recognition_examples/img/unknown/2.jpg')
unknown_face_encoding = face_recognition.face_encodings(unknown_image)[0]

image_of_khedr = face_recognition.load_image_file('C:/Users/YourPc/python face reco/face_recognition_examples/img/known/khedr.jpeg')
khedr_face_encoding = face_recognition.face_encodings(image_of_khedr)[0]

# Compare faces
results = face_recognition.compare_faces([khedr_face_encoding], unknown_face_encoding)
print(type(results[0]))

if results[0]:
    print('This is khedr')
else:
    print('This is NOT khedr')
