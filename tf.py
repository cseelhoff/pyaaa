
import tensorflow as tf
import numpy as np

train_data = np.load('train_data.npy')  
train_labels = np.load('train_labels.npy')
    
model = tf.keras.models.Sequential([
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(
        units=4096,
        kernel_regularizer=tf.keras.regularizers.l2(0.01),
        activation='relu'
        ),
    tf.keras.layers.Dense(
        units=1024,
        kernel_regularizer=tf.keras.regularizers.l2(0.01),
        activation='relu'
        ),
    tf.keras.layers.Dense(
        units=256,
        kernel_regularizer=tf.keras.regularizers.l2(0.01),
        activation='relu'
        ),
    tf.keras.layers.Dense(
        units=1
        )
])

model.compile(
        loss='mse', 
        optimizer=tf.keras.optimizers.Nadam(lr=0.001)
)

history = model.fit(
        x=train_data,
        y=train_labels, 
        epochs=10,
        validation_split=0.1,
        verbose=2,
        batch_size=90000,
        callbacks=[
            tf.keras.callbacks.TensorBoard(log_dir=('./tensorboard/01'))
        ]
)

model.save('model01.h5')
